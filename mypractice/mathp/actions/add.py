import sys

from st2common.runners.base_action import Action

class Addition(Action):
    def run(self, num1,num2):
        sum=num1+num2
        print("The addition of {} and {} is {}".format(num1,num2,sum))
