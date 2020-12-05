import sys
import os
from math import sqrt
import statistics

def main(argv):
    # pageloads = {'wikipedia': [], 'facebook': [], 'amazon': []}
    pageloads = {}

    root_dir = argv[1] if len(argv) > 1 else '.'
    
    # for root, dirs, files in os.walk(os.path.join(root_dir, 'logs')):
    for root, dirs, files in os.walk(root_dir):
        for filename in files:
                if filename == 'pageloads.log':
                    with open(os.path.join(root, filename), 'r') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                                split = [text.rstrip(',')  for text in line.split(' ')]
                                if split[0] == 'Pageload' or i < 2:
                                    continue    # skip header line AND the first page load result because for whatever reason the first page to be loaded takes significantly longer than it would have had it been loaded at any other position in the order
                                if len(split) >= 4:
                                    load_time = split[2]
                                    # print('{}'.format(load_time))
                                    website = split[3]
                                else:
                                    continue

                                # if website == 'http://www.wikipedia.org':
                                #     pageloads['wikipedia'].append(load_time)
                                # elif website == 'http://www.facebook.com':
                                #     pageloads['facebook'].append(load_time)
                                # elif website == 'http://www.amazon.com':
                                #     pageloads['amazon'].append(load_time)
                                # else:
                                #     print('ERROR: website {} not recognized'.format(website))
                                if website not in pageloads:
                                    pageloads[website] = [load_time]
                                else:
                                    pageloads[website].append(load_time)

    for page in pageloads:
        # print(pageloads[page])
        pageloads[page] = [float(load) for load in pageloads[page]]

    # print('N: {}'.format(len(pageloads['wikipedia'])))

    mean = {}
    for page in pageloads:
        # print(page)
        # print(pageloads[page])
        mean[page] = statistics.mean(pageloads[page])

    # variance = {'wikipedia': None, 'facebook': None, 'amazon': None}
    # for page in pageloads:
    #     variance[page] = statistics.variance(pageloads[page])
    #     print(len(pageloads[page]))

    stdev = {}
    for page in pageloads:
        stdev[page] = statistics.stdev(pageloads[page])
    
    for page in sorted(pageloads):
        print('\nwebsite: {}'.format(page))
        # print(pageloads[page])
        print('mean: {0:.2f}s'.format(mean[page] / 1000))
        # print('variance: {}'.format(variance[page]))
        print('standard deviation: {0:.2f}s'.format(stdev[page] / 1000))



if __name__ == '__main__':
    main(sys.argv)
