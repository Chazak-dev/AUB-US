import json

def create_register_message(name,email,username,password,area,driver = False):
    return {
        "type": "Register",
        "data": {
            "name": name,
            "email": email,
            "username": username,
            "password": password,
            "area": area,
            "driver": driver,
        }
    }

def create_login_message(username , password):
    return {
        "type":"Login",
        "data": {
            "username": username,
            "password": password,
        }
    }

def create_ride_request(student_ID , area , time):
    return {
        "type":"Request for a ride",
        "data": {
            "student_ID":student_ID ,
            "area": area,
            "time": time,
        }
    }

def create_accept_ride(driver_ID, ride_ID):
    return {
        "type": "Accept the ride",
        "data": {
            "driver_ID": driver_ID,
            "ride_ID": ride_ID ,
        }
    }