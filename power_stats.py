import sys
import os
import matplotlib.pyplot as plt
from urllib.parse import urlparse
import pathlib

def main(argv):
    if len(argv) != 3:
        print('usage: python3 power_stats.py root_dir exp_name')
        sys.exit(1)

    root_dir = argv[1]
    exp_name = argv[2]

    pathlib.Path('power-{}'.format(exp_name)).mkdir(parents=True, exist_ok=True)

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
    
    # get power statistics

    for root, dirs, files in os.walk('logs'):
        for filename in files:
                if filename == 'power.log':
                    with open(os.path.join(root, filename), 'r') as f:
                        lines = f.readlines()
                        i = 0

                        while i < len(lines):
                            split = [text.rstrip()  for text in lines[i].split(' ')]
                            timestamp = int(split[0]) * 1000   # milliseconds (integer) since the epoch
                            watts = float(split[1])   # Watts used by the system in the past second

                            # resolve timestamp to page load - O(n) with n pages, could improve with sorting plus binary search
                            for page in pageloads:
                                pageload = pageloads[page]
                                if timestamp < pageload.load_start or timestamp > pageload.load_end:
                                    continue

                                pageload.power_measurements.append(watts)
                                break
                                    
                            i += 1

    for website in pageloads:
        print('\nFor website {}'.format(website))
        pageload = pageloads[website]
        # Generate power consumed over time plot for this experiment
        url = urlparse(website)
        domain = url.path.split('/')[1]

        x = [i / len(pageload.power_measurements) for i in range(0, len(pageload.power_measurements))] # normalize timesteps as percent of execution completed
        y = pageload.power_measurements

        # save the plots
        plt.plot(x, y)
        # plt.scatter(x, y)

        plt.gca().set(xlabel='percent of execution completed', ylabel='Power Consumption', title='Site {}'.format(domain))            
        plt.savefig('power-{}/power-{}-{}.png'.format(exp_name, exp_name, domain))
        plt.clf()

                                

class PageLoad():
    def __init__(self, page_name, load_start, load_end):
        self.page_name = page_name
        self.load_start = load_start
        self.load_end = load_end
        self.power_measurements = []    # wattage measurements
        self.power_consumed = 0.0  # cumulative total (Watts)


if __name__ == '__main__':
    main(sys.argv)
