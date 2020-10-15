import os
import sys
import matplotlib.pyplot as plt

def main(argv):
    latencies = {}
    for root, dirs, files in os.walk('logs'):
            for filename in files:
                    if filename == 'func_latencies.log':
                        print('found one')
                        with open(os.path.join(root, filename), 'r') as f:
                            lines = f.readlines()
                            for i, line in enumerate(lines):
                                    split = [text.rstrip(' ')  for text in line.split()]
                                    print(split)
                                    if split[0] in latencies:
                                        latencies[split[0]].append(float(split[1]))
                                    else:
                                        latencies[split[0]] = [float(split[1])]

    for func in latencies:
        
        x = latencies[func]
        plt.hist(x, bins=50)
        plt.gca().set(title='{} Latencies'.format(func), ylabel='Frequency')
        plt.savefig('{}Latencies.png'.format(func))


if __name__ == '__main__':
    main(sys.argv)
