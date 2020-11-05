#include <stdio.h> // printf
#include <stdlib.h> // getenv
#include <string.h>
#include <iostream>
#include <mutex>
#include <string>

#include <stack>

#include <unistd.h> // tid
#include <sys/syscall.h> // get tid
#include <time.h> 
#include <signal.h>
#include <random>

#include"cpu_utils.hh" // affinity functions
#include "ipc.hh"
#include "experimenter.hh"

#include <g3log/g3log.hpp> // logger
#include <g3log/logworker.hpp>

// interface with perf
#define PROF_USER_EVENTS_ONLY
#define PROF_EVENT_LIST \
    PROF_EVENT_CACHE(L1D, READ, MISS) \
    PROF_EVENT_CACHE(L1D, READ, ACCESS) \
    PROF_EVENT_HW(BRANCH_MISSES) \
    PROF_EVENT_HW(BRANCH_INSTRUCTIONS) \
    PROF_EVENT_HW(INSTRUCTIONS) \
    PROF_EVENT_HW(BUS_CYCLES) \
    // PROF_EVENT_CACHE(LL, READ, MISS) \
    PROF_EVENT_CACHE(LL, READ, ACCESS)
#include "prof.h" 


static std::mutex time_mut, config_mut, start_mut, fmap_mut;
static std::atomic<bool> did_start(false), page_loaded(false), config_set(false), page_started(false), external_timing(false);
static std::atomic<int> timeout_s(45);
static int pgid = 0;

static FuncMapType fmap;

std::unique_ptr<g3::LogWorker> worker = nullptr;
std::unique_ptr<g3::FileSinkHandle> handle = nullptr;

thread_local struct timespec time_start,time_end;
thread_local std::random_device rdev;
thread_local std::mt19937 rng;
thread_local std::stack<struct timespec> time_queue;

const unsigned int ns_to_ms = 1000000;

struct timespec page_start, page_end;

struct config_t {
    int nbigs;
    int nlils;
} experiment_config;

void sigalrm_handler( int sig) {
    experiment_stop();

    int result = killpg(pgid,SIGINT);
    if (result != 0) {
        fprintf(stderr,"experimenter.cc: ");
        fprintf(stderr,"Error: could not kill process group: %d;%d\n",pgid,result);
    }
}

void sigint_handler(int sig) {
    experiment_stop();
    ipc_close_mmap();
}

void sigcont_handler(int sig) {
    const std::lock_guard<std::mutex> lock(fmap_mut);
    ipc_update_funcmap(fmap);
}

void set_config(const char* config) {
    //config is in form '4l-4b'
    int bigs = config[0] - '0';
    int lils = config[3] - '0';
    if (bigs > 4 || bigs < 0 || lils > 4 || lils < 0) {
        fprintf(stderr,"experimenter.cc: ");
        fprintf(stderr,"Error: invalid CORE_CONFIG '%s'\n",config);
    }

    const std::lock_guard<std::mutex> lock(config_mut);
    if (!config_set) {
        experiment_config.nbigs = bigs;
        experiment_config.nlils = lils;
        config_set = true;
    }
}

std::string mask_to_str(cpu_set_t mask) {
    std::string result = "XXXXXXXX";
    for (int i = 0; i < 8; i++) {
        if (CPU_ISSET(i,&mask)) {
            result[i] = '1';
        } else {
            result[i] = '0';
        }
    }
    return result;
}

void set_sigint_hndlr() {
    struct sigaction sact;
    sigemptyset(&sact.sa_mask);
    sact.sa_flags = 0;
    sact.sa_handler = sigint_handler;
    sigaction(SIGINT, &sact, NULL);
}

void set_sigcont_hndlr() {
    struct sigaction sact;
    sigemptyset(&sact.sa_mask);
    sact.sa_flags = 0;
    sact.sa_handler = sigcont_handler;
    sigaction(SIGCONT, &sact, NULL);
}

void experiment_start_timer() {
    struct sigaction sact;
    sigemptyset(&sact.sa_mask);
    sact.sa_flags = 0;
    sact.sa_handler = sigalrm_handler;
    sigaction(SIGALRM, &sact, NULL);

    if (!external_timing) {
        alarm(timeout_s); // start timeout
    }
}

void experiment_init(const char *exec_name) {
    const std::lock_guard<std::mutex> lock(start_mut);
    if (did_start) {
        fprintf(stderr,"experimenter.cc: ");
        fprintf(stderr,"Already initialized... exiting\n");
        return;
    }

    // fprintf(stderr,"experimenter.cc: ");
    // fprintf(stderr,"Initializing experiment\n");

    // Init RNG
    char* env_seed = getenv("RNG_SEED");
    if (env_seed != nullptr && atoi(env_seed) != 0) {
        rng.seed(atoi(env_seed));
    } else {
        rng.seed(rdev());
    }

    char* env_timing = getenv("TIMING");
    if (env_timing != nullptr && strncmp(env_timing,"external",9) == 0) { // default to internal timing
        external_timing = true;
    } else if (env_timing != nullptr) {
        int timing_s = atoi(env_timing);
        if (timing_s > 0)
            timeout_s = timing_s; // update time to wait
        else {
            fprintf(stderr,"experimenter.cc: ");
            fprintf(stderr,"Error: invalid TIMING value '%s' \n",env_timing);
        }
    }

    if (external_timing) {
        const std::lock_guard<std::mutex> lock(time_mut);
        clock_gettime(CLOCK_MONOTONIC,&page_start);
        set_sigint_hndlr();
        set_sigcont_hndlr();
    } else {
        experiment_mark_page_start();
    }

    char* ipc = getenv("IPC");
    if (ipc != nullptr && strncmp(ipc,"on",3) == 0) { // default to non-IPC

        char* mmap_file = getenv("MMAP_FILE");
        if (mmap_file == nullptr) {
            fprintf(stderr,"experimenter.cc: ");
            fprintf(stderr,"Error: no MMAP_FILE defined\n");
            exit(1);
        }
        ipc_open_mmap(mmap_file); // TODO figure out where to put ipc_close_mmap
        ipc_update_funcmap(fmap);
    }

    char* env_log = getenv("LOG_FILE");
    if(env_log == nullptr) {
        fprintf(stderr,"experimenter.cc: ");
        fprintf(stderr,"Error: no LOG_FILE defined\n");
        exit(1);
    }
    std::string env_log_str(env_log);

    char* env_config = getenv("CORE_CONFIG");
    if(env_config == nullptr && ipc == nullptr ) {
        fprintf(stderr,"experimenter.cc: ");
        fprintf(stderr,"Error: IPC is not enabled, yet no CORE_CONFIG defined\n");
        exit(1);
    } else if (env_config != nullptr) {
        set_config(env_config);
    }

    std::string logdir,logfile;
    size_t split_spot = env_log_str.find_last_of("/");
    if (split_spot == std::string::npos) {
        logdir = "/home/rock/chrome_research/interpose/logs/";
        logfile = env_log_str;
    } else {
        logdir = env_log_str.substr(0,split_spot);
        logfile = env_log_str.substr(split_spot+1);
    }

    worker=g3::LogWorker::createLogWorker();
    handle=worker->addDefaultLogger(logfile,logdir);

    g3::initializeLogging(worker.get());

    did_start = true; // done initializing, all threads can go now
}

void experiment_start_counters() {
    fprintf(stderr, "starting perf counters\n");
    PROF_START();   // start collecting performance counters
}

void experiment_stop() {
    if (did_start) {
        //fprintf(stderr,"experimenter.cc: ");
        //fprintf(stderr,"\nProgram exceeded %d s limit\n",timeout_s);
        fprintf(stderr, "from experimenter.cc, logging performance counters at end of experiment\n");
        PROF_STDERR();  // log performance counters to error log
        g3::internal::shutDownLogging();
    }
}

void experiment_mark_page_start() {
    if (!page_started && !external_timing) {
        clock_gettime(CLOCK_MONOTONIC,&page_start);
    }
}

void experiment_mark_page_loaded() {
    fprintf(stderr, "!!! tried to mark page as loaded\n");
    if (!page_loaded && !external_timing) {
        clock_gettime(CLOCK_MONOTONIC,&page_end);
        double page_load = -1.0;
        {
            const std::lock_guard<std::mutex> lock(time_mut);
            page_load = ((double)page_end.tv_sec*1000 + (double)page_end.tv_nsec/ns_to_ms)
                - ((double)page_start.tv_sec*1000 + (double)page_start.tv_nsec/ns_to_ms);
            page_loaded = true;
        }

        unsigned int tid = syscall(SYS_gettid);
        LOG(INFO)<< tid << ":\t" << "PageLoadTime\t" << page_load;

    }
}

void experiment_pageload_started(long timestamp) {
    LOG(INFO) << "Website started loading at timestamp: " << timestamp;
}

void experiment_fentry(std::string func_name) {
    unsigned int tid = syscall(SYS_gettid);
#ifdef RUNCHROME_MODE
#warning older version RUNCHROME_MODE
    cpu_set_t mask;
    set_affinity_permute(&mask,rng,experiment_config.nbigs,experiment_config.nlils);
#else
    cpu_set_t mask = fmap[func_name].first;
    set_affinity_with_mask(&mask);
#endif 
    LOG(INFO) << tid << ":\t" << func_name << "\t" << mask_to_str(mask) << "\t" << get_curr_cpu();

    clock_gettime(CLOCK_MONOTONIC,&time_start);
    time_queue.push(time_start); // save the time
}

void experiment_fexit(std::string func_name) {
    clock_gettime(CLOCK_MONOTONIC,&time_end);
    time_start = time_queue.top();
    time_queue.pop();
    double latency = ((double)time_end.tv_sec*1000 + (double)time_end.tv_nsec/ns_to_ms)
                        - ((double)time_start.tv_sec*1000 + (double)time_start.tv_nsec/ns_to_ms);

    unsigned int tid = syscall(SYS_gettid);
#ifdef RUNCHROME_MODE
    cpu_set_t mask;
    set_affinity_all(&mask);
#else
    cpu_set_t mask = fmap[func_name].second;
    set_affinity_with_mask(&mask);
#endif
    char* env_page = getenv("CUR_PAGE");
    if (env_page != nullptr) {
        fprintf(stderr, "!!! %s\n", env_page);
    }
    LOG(INFO) << tid << ":\t" << func_name << "\t" << mask_to_str(mask) << "\t" << get_curr_cpu() << "\t" << latency;
}
