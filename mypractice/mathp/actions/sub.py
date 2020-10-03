import sys

from st2common.runners.base_action import Action

class Sub(Action):
    def run(self, num1,num2):
        sub=num1-num2
        print("The sub of {} and {} is {}".format(num1,num2,sub))
