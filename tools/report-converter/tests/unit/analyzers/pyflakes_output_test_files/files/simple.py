from collections import namedtuple

def get_name():
    # self is undefined
    return self.name

def full_name(self):
    # name is defined but not used
    name = self.first_name + ' ' + self.last_name
    return self.first_name
