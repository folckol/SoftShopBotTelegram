import requests

def create_lst(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    return [line.strip() for line in lines]

addresses = create_lst('1.txt')
keys = create_lst('2.txt')

for i in range(len(keys)):
    print(f'{addresses[i]} {keys[i]}')


