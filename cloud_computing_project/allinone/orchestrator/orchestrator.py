from flask import Flask, render_template, request, jsonify
import json
import requests
import sqlite3
import string
import datetime
import pika
import uuid
import docker
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import time
import math
import operator
from kazoo.client import KazooClient
zk = KazooClient(hosts='zookeeper:2181')
zk.start()
zk.ensure_path("/CC")


app = Flask(__name__)
table = {}
master = {}
number_of_slaves_present = 0
global number_of_slaves_required
number_of_slaves_required = 1

            # flag = 0
    # if flag and children:
        # zk.set("CC/"+children[0],b'master')

def convert_slave_to_master():
    global table
    print("converting a slave to master")
    var = get_min_cont()
    print(var)
    # print(table[var])
    # print(table)
    # del table[var]
    for i in master:
        print("deleting master")
        to_be_deleted = i
    del master[to_be_deleted]
    master[var] = get_pid(var)
    # number_of_slaves_present -= 1


def get_max_cont():
    print(table)
    container_id_max = max(table.items(), key=operator.itemgetter(1))[0]
    # del table[container_id_max]
    return container_id_max

def get_min_cont():
    print(table)
    container_id_min = min(table.items(), key=operator.itemgetter(1))[0]
    del table[container_id_min]
    return container_id_min
    

def get_all_workers_pid():
    l = []
    for slave in table:
        # print(table[slave])
        l.append(table[slave])
    for mast in master:
        l.append(master[mast])
    # print(l)
    l = sorted(l)
    # print(l)
    return l

def spawn_master():
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    # client = docker.from_env()
    string = "python3 -u manager.py 1"
    # l = string.split()
    container = client.containers.run(image="worker",command=string,detach=True,links={"rabbitmq":"rabbitmq"},network="allinone_default")
    print(container.logs())
    container = str(container)
    print(str(container[12:-1]))
    return str(container[12:-1])


def spawn_slave():
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    # client = docker.from_env()
    string = "python3 -u manager.py 0"
    # l = string.split()sla
    container = client.containers.run(image="worker",command=string,detach=True,network="allinone_default")
    print(container.logs())
    container = str(container)
    table[str(container[12:-1])] = get_pid(str(container[12:-1]))
    print(str(container[12:-1]))
    return str(container[12:-1])


def job():
    global number_of_slaves_required
    print("updating count")
    f = open("read_count.txt","r")
    count = f.readline()
    count = int(count)
    print(count)
    f.close()
    f = open("read_count.txt","w")
    f.write("0")
    f.close()
    number_of_slaves_required = int(count)/20
    number_of_slaves_required = math.floor(number_of_slaves_required) + 1
    number_of_slaves_present = len(table)
    print(number_of_slaves_present)
    print(number_of_slaves_required)
    print(table)
    if(number_of_slaves_required > number_of_slaves_present):
        print("printing as spawner")
        while(number_of_slaves_required > number_of_slaves_present):
            spawn_slave()
            # table[variable] = get_pid(variable)
            number_of_slaves_present += 1
    else:
        while(number_of_slaves_required < number_of_slaves_present):
            container_id_max = max(table.items(), key=operator.itemgetter(1))[0]
            # time.sleep(60)
            stop_docker_using_container_id(container_id_max)
            del table[container_id_max]
            number_of_slaves_present -= 1


def incremnet_read_count():
    f = open("read_count.txt","r")
    count = f.readline()
    count = int(count)
    count += 1 
    print(count)
    f.close()
    f = open("read_count.txt","w")
    f.write(str(count))
    f.close()    


#client.get()

def get_pid(container_id):
    # string = "docker inspect -f '{{.State.Pid}}' "+container_id
    # l = string.split(" ")
    # process = subprocess.Popen(l, stdout=subprocess.PIPE)
    # stdout = process.communicate()[0]
    # string = stdout.decode("utf-8")
    # print(string)
    # string = string.strip()
    # print(string)
    # string = string[1:-1]
    # print(string)
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    x = client.containers.get(container_id)
    y = x.top()
    z = y["Processes"]
    pid = z[0][2]
    return (int(pid))

def stop_docker_using_container_id(container_id):
    # string = "docker stop "+ container_id
    # l = string.split(" ")
    # process = subprocess.Popen(l, stdout=subprocess.PIPE)
    # stdout = process.communicate()[0]
    # string = stdout.decode("utf-8")
    # string = string.strip()
    # print (string)
    # string = "docker rm "+container_id
    # l = string.split(" ")
    # process = subprocess.Popen(l, stdout=subprocess.PIPE)
    # stdout = process.communicate()[0]
    # string = stdout.decode("utf-8")
    # string = string.strip()
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    x = client.containers.get(container_id)
    x.stop()
    x.remove()
    # return (string)


class reading(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq'))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='ResponseQ', durable=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body
            ch.basic_ack(delivery_tag = method.delivery_tag)

    def call(self, q , n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.queue_declare(queue = 'readQ', durable=True)
        self.channel.basic_publish(
            exchange='',
            routing_key='readQ',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=n)

        while self.response is None:
            #print("recieved nothing")
            self.connection.process_data_events()
        return (self.response.decode("utf-8"))


@zk.ChildrenWatch("/CC")
def start_zookeeping(children):
    global number_of_slaves_required
    print("There are %s children with names %s" % (len(children), children))
    flag = 0
    for i in children:
        data,stat = zk.get("CC/"+i)
        x = data.decode("utf-8")
        print("Child: %s  ---  Data: %s" % (i, data.decode("utf-8")))
        if x=="master" :
            print("{} is the master".format(i))
            flag = 1
    if(flag != 1 and children):
        zk.set("CC/"+children[0],b'master')
        convert_slave_to_master()
    print(len(children)-1, number_of_slaves_required)
    if(len(children)-1 < number_of_slaves_required and len(children) != 0):
        print("A slave has been died")
        spawn_slave()

@app.route('/api/v1/db/write', methods=['POST'])
def write_db():
    print("write")
    data = request.json['insert']
    column = request.json['column']
    table = request.json['table']
    what = request.json['what']
    if(what == "delete"):
        print("deleting")
        print(data)
        query = "DELETE FROM "+table+" where "+data
    else:
        print("inserting")
        query = "INSERT INTO "+table+" ("+column+") "+"VALUES ("+data+")"
    # write = writing()
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()

    channel.queue_declare(queue='writeQ', durable=True)

    channel.basic_publish(exchange='', routing_key='writeQ', body= query)
    f = open("logs.txt","a")
    f.write(query+"\n")
    f.close()
    print("sent query", query)
    connection.close()  
    # response = write.call("writeQ",query)
    # print(response)
    res = jsonify()
    return res, 201

#9
@app.route('/api/v1/db/read', methods=['POST'])
def read():
    incremnet_read_count()
    print("read")
    table = request.json['table']
    columns = request.json['columns']
    where = request.json['where']
    query = "SELECT "+columns+" FROM "+table+" WHERE "+where
    print(query)
    reader = reading()
    response = reader.call("readQ",query)
    print(response)
    # response = fibonacci_rpc.call("readQ",1)
    # response = json.loads(response)
    print(response)
    return response, 200


@app.route('/api/v1/db/new_slave', methods=['POST'])
def new_slave():
    f = open("logs.txt","r")
    readed = f.read()
    readed = readed.split("\n")
    readed = readed[:-1]
    print(readed)
    f.close()
    # new_dict = {"data":str(readed)}
    return json.dumps(readed), 200


@app.route('/api/v1/db/clear', methods=['POST'])
def clear_db():
    # print("Clearing DB")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()

    channel.queue_declare(queue='writeQ', durable=True)
    queries = []
    queries.append("DELETE FROM users")
    queries.append("DELETE FROM ride")
    queries.append("DELETE FROM join_ride")
    for query in queries:
        channel.basic_publish(exchange='', routing_key='writeQ', body= query)
        print("sent query", query)
    connection.close()
    f = open("logs.txt","a")
    for query in queries:
        f.write(query+"\n")
    f.close()
    # response = write.call("writeQ",query)
    # print(response)
    res = jsonify()
    return res, 200

scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(
    func=job,
    trigger=IntervalTrigger(seconds=120),
    id='job_creater',
    name='clean read.txt time every 120 seconds',
    replace_existing=True)
# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/api/v1/crash/master', methods=['POST'])
def crash_master():
    for mast in master:
        pid = master[mast]
        stop_docker_using_container_id(mast)
    l =[]
    l.append(pid)
    return json.dumps(l), 200

@app.route('/api/v1/crash/slave', methods=['POST'])
def crash_slave():
    container_id_max = get_max_cont()
    # time.sleep(60)
    pid = get_pid(container_id_max)
    stop_docker_using_container_id(container_id_max)
    del table[container_id_max]
    print(table)
    l = []
    l.append(pid)
    return json.dumps(l), 200

@app.route('/api/v1/worker/list', methods=['GET'])
def list_worker():
    # client = docker.from_env()
    # return client.containers.list()
    something = get_all_workers_pid()
    print(something)
    return json.dumps(something), 200


if __name__ == '__main__':
    # job()
    # start_zookeeping()
    f = open("logs.txt","w")
    f.close()
    variable =  spawn_master()
    master[variable] = get_pid(variable)
    print("master")
    # number_of_slaves_required = 1
    # spawn_slave()
    # print("slave")
    app.debug=False
    app.run(host="0.0.0.0",port=80,use_reloader=False)