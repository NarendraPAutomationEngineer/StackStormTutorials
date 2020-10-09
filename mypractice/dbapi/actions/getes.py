import sys
import requests
from st2common.runners.base_action import Action

class Dbgetes(Action):
    def run(self):
        url="http://dummy.restapiexample.com/api/v1/employees"
        response = requests.get('http://dummy.restapiexample.com/api/v1/employees')         
        if response.status_code == 200:
            print(response.json())
            return(True,200)
        return(False,"Failed!")
