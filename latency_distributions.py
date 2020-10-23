import os
import sys
import matplotlib.pyplot as plt
import pathlib

def main(argv):
    if len(argv) < 2:
        print('usage: python3 latency_distributions.py path_to_experiment')

    DIR = 'histograms/'
    pathlib.Path(DIR).mkdir(parents=True, exist_ok=True)
    latencies = {}
    for root, dirs, files in os.walk(os.path.join(argv[1], 'logs')):
            for filename in files:
                    if filename == 'func_latencies.log':
                        # print('found one')
                        with open(os.path.join(root, filename), 'r') as f:
                            lines = f.readlines()
                            for i, line in enumerate(lines):
                                    split = [text.rstrip(' ')  for text in line.split()]
                                    # print(split)
                                    if split[0] in latencies:
                                        latencies[split[0]].append(float(split[1]))
                                    else:
                                        latencies[split[0]] = [float(split[1])]

    colors = ['tab:red', 'tab:blue', 'tab:green', 'tab:pink', 'tab:olive']

    if len(argv) == 3 and argv[2] == 'combined':
        i = 0
        for func in latencies:
            
            x = latencies[func]
            plt.hist(x, bins=50, density=True, stacked=True, alpha=0.5, color=colors[i], label=func)

            i += 1

        plt.gca().set(title='All Function Latencies', ylabel='Frequency', xlabel='Latency (ms)')
        plt.xlim(0,500)
        plt.legend()
        plt.savefig('{}Combined.png'.format(DIR))
        plt.clf()

    else:
        i = 0
        for func in latencies:
            x = latencies[func]
            plt.hist(x, bins=50, color=colors[i])
            # print(colors[i])
            plt.gca().set(title='{} Latencies'.format(func), ylabel='Frequency', xlabel='Latency (ms)')
            plt.savefig('{}{}Latencies.png'.format(DIR, func))
            plt.clf()

            i += 1


if __name__ == '__main__':
    main(sys.argv)
