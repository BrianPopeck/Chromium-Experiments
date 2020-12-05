import sys
import os
import matplotlib.pyplot as plt
from urllib.parse import urlparse
import pathlib
import statistics

def main(argv):
    if len(argv) < 2:
        print('usage: python3 power_stats.py root_dir [exp_name]')
        sys.exit(1)

    root_dir = argv[1]
    exp_name = argv[2] if len(argv) >= 3 else None
    
    power_per_trial = {}
    trial_num = 0   # note we iterate through trials in arbitrary order, not chronological
    
    for root, dirs, files in os.walk(root_dir):
        if len([x for x in files if (x == 'pageloads.log' or x == 'power.log')]) != 2:
            continue

        pageloads = {}  # mapping website name to Pageload object

        # get page load start and end times
        with open(os.path.join(root, 'pageloads.log'), 'r') as f:
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

        # compute power statistics for this trial
        with open(os.path.join(root, 'power.log'), 'r') as f:
            lines = f.readlines()
            i = 0

            while i < len(lines):
                split = [text.rstrip()  for text in lines[i].split(' ')]
                timestamp = int(split[0]) * 1000   # milliseconds (integer) since the epoch
                watts = float(split[1])   # Watts used by the system in the past second

                # resolve timestamp to page load - O(n) with n pages, could improve with sorting plus binary search
                for page in pageloads:
                    pageload = pageloads[page]

                    # assuming that power measurement at time t is the wattage used by the system between time t-1 and t
                    # thus we need to consider one measurement after the page load ends to get a partial interval
                    # print('timestamp: {}, pageload start: {}, pageload end: {}', timestamp, pageload.load_start, pageload.load_end)
                    if timestamp < pageload.load_start or timestamp >= pageload.load_end + 1:
                        continue

                    pageload.power_measurements.append(watts)
                    break
                        
                i += 1

        for website in pageloads:
            pageload = pageloads[website]

            url = urlparse(website)
            domain = url.path.split('/')[1]

            # Print out total power for this page for this trial

            if len(pageload.power_measurements) == 0:
                print('ERROR: no power measurements detected for site {}'.format(domain))
            else:
                # scale average wattage by length of interval to mitigate impact of missing values for certain timestamps
                # TODO: implement a more sophisticated way to deal with missing data
                total = statistics.mean(pageload.power_measurements) if len(pageload.power_measurements) > 1 else pageload.power_measurements[0]
                print('one trial\'s average power consumption for {0:}: {1:.2f}W'.format(domain, total))
                total *= (pageload.load_end - pageload.load_start) / 1000   
                print('one trial\'s total energy consumption for {0:}: {1:.2f}W'.format(domain, total))
                if website not in power_per_trial:
                    power_per_trial[website] = [total]
                else:
                    power_per_trial[website].append(total)

            if exp_name is None:    # exit before generating plots if necessary
                continue
            
            # Generate power consumed over time plot for this experiment

            pathlib.Path('power-{}'.format(exp_name)).mkdir(parents=True, exist_ok=True)

            x = [i / len(pageload.power_measurements) for i in range(0, len(pageload.power_measurements))] # normalize timesteps as percent of execution completed
            y = pageload.power_measurements

            # save the plots
            plt.plot(x, y)
            # plt.scatter(x, y)

            plt.gca().set(xlabel='percent of execution completed', ylabel='Power Consumption', title='Site {}'.format(domain))            
            plt.savefig('power-{}/trial{}-power-{}.png'.format(exp_name, trial_num, domain))
            plt.clf()     
        
        trial_num += 1


    # compute average power consumption across all trials
    for website in sorted(power_per_trial):
        url = urlparse(website)
        domain = url.path.split('/')[1]
        
        power_consumption = None
        if len(power_per_trial[website]) > 1:
            power_consumption = statistics.mean(power_per_trial[website])
        elif len(power_per_trial[website]) == 1:
            power_consumption = power_per_trial[website][0]
        else:
            print('ERROR: no energy consumption data for site {}'.format(domain))
            continue

        print('Total energy consumed for {0:}: {1:.2f}W'.format(domain, power_consumption))


class PageLoad():
    def __init__(self, page_name, load_start, load_end):
        self.page_name = page_name
        self.load_start = load_start
        self.load_end = load_end
        self.power_measurements = []    # wattage measurements

    def __repr__(self):
        return 'Page: {}, Start: {}, End: {}'.format(self.page_name, self.load_start, self.load_end)


if __name__ == '__main__':
    main(sys.argv)
