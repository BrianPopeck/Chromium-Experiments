.PHONY=clean run clearlogs

PERM_PREFIX:=+site

default: libintercept.so

run: logs/ libintercept.so
	./permutate.sh -c './run-chrome.sh' -f '-w +url -v' -p '$(PERM_PREFIX)'

runv: logs/ libintercept.so
	./permutate.sh -c './run-chrome.sh' -f '-w +url -vi' -p '$(PERM_PREFIX)'


logs/:
	mkdir logs/

libintercept.so: chrome_intercept.cc experiment/cpu_utils.* experiment/experimenter.*
	clang++ -g -shared -fPIC -ldl -lg3logger -o libintercept.so chrome_intercept.cc experiment/cpu_utils.cc experiment/experimenter.cc

clean:
	-@rm *.so *.out 2>/dev/null || true

clearlogs:
	-@rm logs/*.log 2>/dev/null || true
