import sys
import os
import matplotlib.pyplot as plt
from urllib.parse import urlparse
import pathlib

TIMESTEP = 100  # milliseconds

def main(argv):
    if len(argv) != 3:
        print('usage: python3 perf_counters.py root_dir exp_name')
        sys.exit(1)

    root_dir = argv[1]
    exp_name = argv[2]

    pathlib.Path('cpi-{}'.format(exp_name)).mkdir(parents=True, exist_ok=True)

    # get page load start and end times
    
    pageloads = {}
    
    for root, dirs, files in os.walk(os.path.join(root_dir, 'logs')):
        for filename in files:
                if filename == 'pageloads.log':
                    with open(os.path.join(root, filename), 'r') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                                split = [text.rstrip(',')  for text in line.split(' ')]
                                if split[0] == 'Pageload' or i < 2:
                                    continue    # skip header line
                                if len(split) >= 4:
                                    load_start = float(split[1])
                                    load_duration = float(split[2])
                                    website = split[3]
                                else:
                                    continue

                                pageloads[website] = PageLoad(website, load_start, load_start + load_duration)


    processes = {}
    
    # get perf counter dumps

    for root, dirs, files in os.walk('logs'):
        for filename in files:
                if filename == 'PyChrome-chrome-err.log':
                    with open(os.path.join(root, filename), 'r') as f:
                        lines = f.readlines()
                        i = 0
                        while i < len(lines):
                            split = [text.rstrip(',')  for text in lines[i].split(' ')]
                            if split[0] == 'PROCESS_START':
                                ptype = split[1]
                                pid = int(split[2])
                                processes[pid] = Process(pid, ptype)
                            elif split[0] == 'PERF_DUMP':
                                pid = int(split[1])
                                timestamp = float(split[2])
                                dump = PerfDump(timestamp)
                                
                                j = 0
                                while j < len(PerfDump.perf_events):
                                    i += 1
                                    # Chrome itself may have output to err log in the middle of the data, so skip the line if so
                                    try:
                                        first = lines[i].split()[0]
                                        if int(first) < 0 or int(first) >= len(PerfDump.perf_events):
                                            continue
                                    except ValueError:  # the first item is not an integer
                                        continue

                                    dump.counters.append(int(lines[i].split()[1]))
                                    j += 1

                                # resolve dump to page load
                                for page in pageloads:
                                    pageload = pageloads[page]
                                    if timestamp <= pageload.load_start or timestamp >= pageload.load_end + TIMESTEP:
                                        continue

                                    dump.website = page
                                    if timestamp > pageload.load_end:
                                        dump.weight = 1.0 - ((timestamp - pageload.load_end) / TIMESTEP)
                                    elif timestamp < pageload.load_start + TIMESTEP:
                                        dump.weight = (timestamp - pageload.load_start) / TIMESTEP
                                    else:
                                        dump.weight = 1.0

                                processes[pid].perf_dumps.append(dump)
                                    
                            i += 1

    for website in pageloads:
        print('\nFor website {}'.format(website))
        for pid in processes:
            summed_metrics = []
            cpi = None
            l1d_miss_rate = None
            branch_misprediction_rate = None

            print('For {} process {}\n'.format(processes[pid].ptype, pid))
            perf_dumps = [perf_dump for perf_dump in processes[pid].perf_dumps if perf_dump.website == website]
            for i in range(len(PerfDump.perf_events)):
                summed_metrics.append(sum([perf_dump.weight * perf_dump.counters[i] for perf_dump in perf_dumps]))
                print('{}: {}'.format(PerfDump.perf_events[i], summed_metrics[i]))
            print('')

            if summed_metrics[4] > 0:
                cpi = summed_metrics[6] / float(summed_metrics[4])
                print('CPI: {}'.format(cpi))
            if summed_metrics[1] > 0:
                l1d_miss_rate = summed_metrics[0] / float(summed_metrics[1])
                print('L1D miss rate: {}'.format(l1d_miss_rate))
            if summed_metrics[3] > 0:
                branch_misprediction_rate = summed_metrics[2] / float(summed_metrics[3])
                print('Branch misprediction rate: {}'.format(branch_misprediction_rate))
            print('')

            # Generate CPI over time plot for this experiment
            url = urlparse(website)
            domain = url.path.split('/')[1]
            if summed_metrics[4] == 0:   # no instructions executed, so no CPI to calculate
                print('skipping plotting for site {} and process {}'.format(domain, pid))
                continue

            x = []
            y = []
            for perf_dump in perf_dumps:
                if perf_dump.counters[4] == 0:  # no instructions, so no CPI at this timestep
                    continue
                x.append(perf_dump.timestamp)
                y.append(perf_dump.counters[6] / float(perf_dump.counters[4]))

            # normalize timestamp to be relative to length of execution
            time_start = x[0]
            time_end = x[-1]
            range_timestamp = time_end - time_start
            x = [((timestamp - time_start) / range_timestamp) * 100 for timestamp in x]

            # save the plots
            # plt.plot(x, y)
            plt.scatter(x, y)

            plt.gca().set(xlabel='percent of execution completed', ylabel='CPI in most recent timestep', title='Site {} and {} process {}'.format(domain, processes[pid].ptype, pid))            
            plt.savefig('cpi-{}/cpi-{}-{}-{}.png'.format(exp_name, exp_name, domain, pid))
            plt.clf()

                                

class PageLoad():
    def __init__(self, page_name, load_start, load_end):
        self.page_name = page_name
        self.load_start = load_start
        self.load_end = load_end

class Process():
    def __init__(self, pid, ptype):
        self.pid = pid
        self.ptype = ptype
        self.perf_dumps = []

class PerfDump():
    perf_events = ['L1D Read Miss', 'L1D Read Accesses', 'Branch Misses', 'Branch Instructions', 'Instructions', 'Bus Cycles', 'CPU Cycles']
    
    def __init__(self, timestamp):
        self.timestamp = timestamp
        self.counters = []
        self.website = None # associated website
        self.weight = 1.0   # weight for overlap with page load

    




if __name__ == '__main__':
    main(sys.argv)
