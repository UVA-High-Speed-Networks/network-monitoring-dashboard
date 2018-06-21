import sys
import glob
import os


def get_new_name(old_name):
	try:
		prefix = int(old_name[-2])
	except ValueError:
		prefix = 1
	split = os.path.split(old_name)
	split = list(split)
	split[-1] = "{}-{}".format(prefix, split[-1])
	return os.path.join(*split)

def main(path):
	logs = glob.glob(os.path.join(path, "*.log*"))
	for l in logs:
		os.rename(l, get_new_name(l))


if __name__ == "__main__":
	path = sys.argv[1]
	main(path)