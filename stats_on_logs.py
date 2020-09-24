import sys
import os
from math import sqrt
import statistics

def main(argv):
    pageloads = {'wikipedia': [], 'facebook': [], 'amazon': []}
    
    for root, dirs, files in os.walk('logs'):
        for filename in files:
                if filename == 'pageloads.log':
                    with open(os.path.join(root, filename), 'r') as f:
                        lines = f.readlines()
                        for line in lines:
                                split = [text.rstrip(',')  for text in line.split()]
                                print(split)
                                if split[0] == 'Pageload':
                                    continue
                                if len(split) >= 4:
                                    load_time = split[2]
                                    website = split[3]
                                else:
                                    continue

                                if website == 'http://www.wikipedia.org':
                                    print('adding to wiki')
                                    # pageloads['wikipedia'] += load_time
                                    pageloads['wikipedia'].append(load_time)
                                elif website == 'http://www.facebook.com':
                                    # pageloads['facebook'] += load_time
                                    pageloads['facebook'].append(load_time)
                                elif website == 'http://www.amazon.com':
                                    # pageloads['amazon'] += load_time
                                    pageloads['amazon'].append(load_time)
                                else:
                                    print('ERROR: website {} not recognized'.format(website))

    print(pageloads['wikipedia'])

    for page in pageloads:
        pageloads[page] = [float(load) for load in pageloads[page]]

    mean = {'wikipedia': None, 'facebook': None, 'amazon': None}
    for page in pageloads:
        print(page)
        print(pageloads[page])
        mean[page] = sum(pageloads[page]) / len(pageloads[page])

    variance = {'wikipedia': None, 'facebook': None, 'amazon': None}
    for page in pageloads:
        # variance[page] = sum((x_i - mean[page])**2 for x_i in pageloads[page]) / len(pageloads[page])
        variance[page] = statistics.variance(pageloads[page])
        print(len(pageloads[page]))

    stddev = {'wikipedia': None, 'facebook': None, 'amazon': None}
    for page in pageloads:
        stddev[page] = sqrt(variance[page])
    
    for page in pageloads:
        print('\nwebsite: {}'.format(page))
        print(pageloads[page])
        print('\nmean: {}'.format(mean[page]))
        print('variance: {}'.format(variance[page]))
        print('standard deviation: {}'.format(stddev[page]))



if __name__ == '__main__':
    main(sys.argv)
