import sys
import os

TIMESTEP = 100  # milliseconds

def main(argv):
    # get page load start and end times
    
    pageloads = {}
    
    for root, dirs, files in os.walk('logs'):
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

                                # if website not in pageloads:
                                #     pageloads[website] = [PageLoad(website, load_start, load_start + load_duration)]
                                # else:
                                #     pageloads[website].append(PageLoad(website, load_start, load_start + load_duration))

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
        print('For website {}'.format(website))
        for pid in processes:
            print('For process {}'.format(pid))
            perf_dumps = [perf_dump for perf_dump in processes[pid].perf_dumps if perf_dump.website == website]
            for i in range(len(PerfDump.perf_events)):
                summed_metric = sum([perf_dump.weight * perf_dump.counters[i] for perf_dump in perf_dumps])
                print('{}: {}'.format(PerfDump.perf_events[i], summed_metric))
                                

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
    perf_events = ['L1D Read Miss', 'L1D Read Access', 'Branch Misses', 'Branch Instructions', 'Instructions', 'Bus Cycles', 'CPU Cycles']
    
    def __init__(self, timestamp):
        self.timestamp = timestamp
        self.counters = []
        self.website = None # associated website
        self.weight = 1.0   # weight for overlap with page load

    




if __name__ == '__main__':
    main(sys.argv)
