from flask import Flask

from flask_pymongo import PyMongo

from bson.json_util import dumps

from bson.objectid import ObjectId

from flask import jsonify, request

import json

import logging

import re

import operator

import telnetlib

app = Flask(__name__)

#app.config['MONGO_URI'] = "mongodb://localhost:27017/ReactDatabase"

app.config['MONGO_URI'] = "mongodb://172.17.0.1:27018/ReactDatabase"

app.config['SECRET_KEY'] = 'secret!'

mongo = PyMongo(app)

logging.basicConfig(filename="info.log", level=logging.DEBUG)

@app.route('/telnet' , methods=['GET','POST'])
def flowList():
    try:
        global reqNo
        reqNo = request.args.get('reqNo')
        if reqNo == None:
            return "reqNo key missing"
        #print (reqNo)
        reqNo = int(reqNo)
        
        global name,nodeDetail,receiveVar,commandOutput,resultArray
        resultArray=[]
        name = request.args.get('flowname')
        global isOpen
        isOpen = False
        receiveVar = ""
        if name == None:
            logging.info('Id : %d -FlowName key  missing',reqNo)
            return "flowname key missing"
        else:
            flowList = mongo.db.FlowListCollection.find_one({'name':name})
            resp = dumps(flowList)
            if resp == "null":
                logging.info('Id : %d - Invalid FlowName',reqNo)
                return "invalid flowname "
            else:
                logging.info('Id : %d - flow name : %s',reqNo,name)
                resultArray.append({'variable':'flowname','value':name,'isRemove':False})
                returnVal = checkAction(name,"Step1")
                return returnVal
    except TypeError:
        return " type error"
    except Exception as e:
        return str(e)

def checkAction(flowname,stepno):
    global variableDoc
    logging.info("Id : %d - Executing %s",reqNo,stepno)
    try:
        variableDoc = mongo.db.FlowContent.find_one({'Flow':flowname , 'Step':stepno})
        #print "variableDoc",variableDoc
        if variableDoc != None:
            action = variableDoc["Action"]
            if len(action) > 0:   #check if action is available
                for actionContent in action:
                    rval = actionFunction(actionContent)
            else:
                rval = checkCondition1()
            
            return rval
        else:
            return "Wrong configuration"
    except Exception as e:
        return str(e)
        #return "exception raised in check Action function"
            
def checkCondition1():
    #print "in check condition",resultArray
    ops = { "==": operator.eq, "!=": operator.ne , "<":operator.lt, "<=":operator.le, ">":operator.gt, ">=":operator.ge }
    opsArray = ["==", "!=","<","<=",">",">="]
    link = variableDoc["Link"]  
    ismatch = False  
    try:
        if len(link) > 0:
            for i in link:
                if ismatch == False:
                    if i["Condition"] == "true":
                        val = execCondition(i)
                        ismatch = True
                    else:
                        for opr in opsArray:
                            if opr in i["Condition"]:
                                #print i["Condition"].split(opr) 
                                splitCondition = i["Condition"].split(opr)
                                for r in resultArray:
                                    if ismatch == False:
                                        l_val = splitCondition[0].lower().strip()
                                        r_val = splitCondition[1].lower().strip()
                                        if (l_val == r["variable"].lower() and ops[opr](r["value"].lower(),r_val)):
                                            val = execCondition(i)
                                            ismatch = True
                            
        if ismatch == False:
            val = "Wrong Configuration"
        return val
    except:
        return "exception raised while checking condition"
    
                                            
def execCondition(i):
    try:
        refreshArray()
        nextstepType = i["NextStep"]["path"]
        nextStep = i["NextStep"]["name"]
        if nextStep == "":
            return "step not configured"
        if nextstepType == "Flow":
            global name
            name = nextStep
            logging.info("Next Operation - %s",name)
            val = checkAction(name,"Step1")
            return val
        else:
            val = checkAction(name,nextStep)
            return val
    except Exception as e:
        return str(e)

def refreshArray():
    
    global resultArray
    newList = []
    for r in resultArray:
       if r["isRemove"] == False:
            newList.append(r)
    resultArray = newList  
    

def actionFunction(action):
    actionType = action["Type"]
    logging.info("Id : %d - Action - %s",reqNo,actionType)
    global val,successStep,failStep,severInfo,successType,failType,isSuccess,isFail,receiveVar,commandOutput,resultArray
    #resultArray = []
    isSuccess = False
    isFail = False
    if actionType == "Receive Variable":
        try:
            #global resultArray
            print ("rv")
            #receiveVar = action["variable"]
            #print receiveVar
            #argVar = request.args.get(action["variable"])
            isValue = False
            
            for variable in action["variable"]:
                print (variable)
                reqVal = request.args.get(variable)
                print (reqVal)
                
                logging.info("Id : %d - variable: %s, value:%s",reqNo,variable,reqVal)
                if reqVal == None or reqVal == "":
                    isValue = True
                else:
                    resultobj = {'variable':variable , 'value':reqVal , 'isRemove':False}
                    resultArray.append(resultobj)
                    print (resultArray)
            
            if isValue == True: #check if argument has empty variable or argument undefined
                resultobj = {'variable':'returnAction','value':'Failure','isRemove':True}
                resultArray.append(resultobj)
                
            else:
                resultobj = {'variable':'returnAction','value':'Success','isRemove':True}
                resultArray.append(resultobj)
            
            val = checkCondition1()
        except Exception as e:
            val = str(e)
            

    elif actionType == "Add Text Message" or actionType == "Add Json Object":
        logging.info("Id : %d - Text message : %s",reqNo, action["message"])
        try:
            
            val = action["message"]
            char1 = '{'
            char2 = '}'
            charCount = val.count(char1)
            dupVal = val
            outArray=[]
            for i in range(charCount):
                outVar1 = dupVal[dupVal.find(char1)+1 : dupVal.find(char2)]
                outArray.append(outVar1)
                dupVal = dupVal.partition('}')[2]   
                
            #print outArray

            if len(resultArray)>0:
                for result in resultArray:
                    for outVar in outArray:
                        #print (result) 
                        if result["variable"] == outVar:
                            
                            replaceValue = "{"+outVar+"}"
                            if type(result["value"]) == list:
                                output = ' '.join(str(e) for e in result["value"])
                                # print output
                                lst = result["value"]
                                output1 = {"value"+str(v): k for v, k in enumerate(lst)}
                                # output1={}
                                # print "list",lst
                                # for index,value in enumerate(lst):
                                #     print value,index
                                #     output1.update({"value"+str(index):value})
                                if actionType == "Add Text Message":
                                    val = val.replace(replaceValue,output)
                                elif actionType == "Add Json Object":
                                    val = output1
                            else:
                                val = val.replace(replaceValue,result["value"])
        except Exception as e:
            val = "exception raised - Add Text Message - "+str(e)

    elif actionType == "Find NodeDetails":
        print ("find node detail")
        #print receiveVar
        #if receiveVar == "":
        nodeArg = request.args.get("nodename")
        #else:
        #    nodeArg = request.args.get(receiveVar)
        if nodeArg == None: 
            val = "Variable not sent"
        elif nodeArg == "":
            val = "Value not sent"
        else:
            try:
                global nodeDetail
                nodeDetail = mongo.db.NodeCollection.find_one({'Node_Name':nodeArg})
                #print ("nodeDetail" , nodeDetail)
                logging.info("Id : %d - node Details - %s",reqNo,nodeDetail)
                if nodeDetail == None:
                    resultobj = {'variable':'returnAction','value':'Failure','isRemove':True}
                    resultArray.append(resultobj)
                
                else:
                    
                    #checkNodeType(nodeDetail)
                    serverDetail = mongo.db.ServerDetailsCollection.find_one({'Server_Id':nodeDetail["Server_Id"]})
                    global serverInfo
                    print (serverDetail["Server_Name"])
                    nodeInfo = {
                    "nodetype":nodeDetail["Node_Type"],
                    "Vendor":nodeDetail["Vendor"],
                    "Server":serverDetail["Server_Name"]
                    }
                # val = output
                    logging.info("Id : %d - node Details - %s",reqNo,nodeInfo)
                    serverInfo = serverDetail
                    resultArray.append({'variable':'returnAction','value':'Success','isRemove':True})
                    resultArray.append({'variable':'nodetype','value':nodeDetail["Node_Type"],'isRemove':False})
                    resultArray.append({'variable':'vendortype','value':nodeDetail["Vendor"],'isRemove':False})
                val = checkCondition1()
            except Exception as e:
                #val = "exception raised - Find node details"
                val = str(e)
               
    elif actionType == "Get SNMP Command":
        print ("snmp")
        version = serverInfo["version"]
        print (version)
        if (version == 1 or version == 2):
            print (serverInfo)
            print (action)
            community_string = serverInfo["community_string"]
            snmp_agent_ip = serverInfo["IPAddress"]
            snmp_port = int(serverInfo["port"])
            object_types = []
            for oid in action["oid"]:
                print (oid["value"])
                object_types.append(ObjectType(ObjectIdentity(oid["value"])))
                print (object_types)

            #oid = action["oid"][0]["value"]
            iterator = getCmd(SnmpEngine(),
                  CommunityData(community_string),
                  UdpTransportTarget((snmp_agent_ip, snmp_port)),
                  ContextData(),
                  *object_types)
                  #ObjectType(ObjectIdentity(oid)))
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            if errorIndication:  # SNMP engine errors
                print(errorIndication)
                resultArray.append({'variable':'returnAction','value':'Failure','isRemove':True})
            else:
                if errorStatus:  # SNMP agent errors
                    resultArray.append({'variable':'returnAction','value':'Failure','isRemove':True})
                    print('%s at %s' % (errorStatus.prettyPrint(),
                            varBinds[int(errorIndex)-1] if errorIndex else '?'))
                else:
                    outputstring = ""
                    for varBind in varBinds:  # SNMP response contents
                        print(varBind)
                        outputstring = outputstring+ '\n'+str(varBind)
                        resultArray.append({'variable':'returnAction','value':'Success','isRemove':True})
                    resultArray.append({'variable':action["variable"],'value':outputstring,'isRemove':False})
                        #print(' = '.join([x.prettyPrint() for x in varBind]))
            val = checkCondition1()
        elif (version == 3):
            snmp_user = serverInfo["username"]
            auth_password = serverInfo["auth_password"]
            priv_pass = serverInfo["priv_pass"]
            snmp_agent_ip = serverInfo["IPAddress"]
            snmp_port = int(serverInfo["port"])
            object_types = []
            for oid in action["oid"]:
                print (oid["value"])
                object_types.append(ObjectType(ObjectIdentity(oid["value"])))
                print (object_types)

            #oid = action["oid"][0]["value"]
            #print("oid",object_types)
            iterator = getCmd(SnmpEngine(),
                  UsmUserData(snmp_user, auth_password, priv_pass,
                 authProtocol=usmHMACMD5AuthProtocol,
                 privProtocol=usmDESPrivProtocol),
                  UdpTransportTarget((snmp_agent_ip, snmp_port)),
                  ContextData(),
                  *object_types)
             #     ObjectType(ObjectIdentity(oid)))
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            if errorIndication:  # SNMP engine errors
                print(errorIndication)
                resultArray.append({'variable':'returnAction','value':'Failure','isRemove':True})
            else:
                if errorStatus:  # SNMP agent errors
                    resultArray.append({'variable':'returnAction','value':'Failure','isRemove':True})
                    print('%s at %s' % (errorStatus.prettyPrint(),
                            varBinds[int(errorIndex)-1] if errorIndex else '?'))
                else:
                    outputstring = ""
                    for varBind in varBinds:  # SNMP response contents
                        print(varBind)
                        outputstring = outputstring+ '\n'+str(varBind) 
                        resultArray.append({'variable':'returnAction','value':'Success','isRemove':True})
                    resultArray.append({'variable':action["variable"],'value':outputstring,'isRemove':False})
                        #print(' = '.join([x.prettyPrint() for x in varBind]))
            val = checkCondition1()


    elif actionType == "Connect":
        print ("connect")

        hostname = request.args.get('hostname')
        if hostname == None:
            return 'hostname key missing'
        username = request.args.get('username')
        if username == None:
            return 'username key missing'
        password = request.args.get('password')
        if password == None:
            return 'password key missing'
        connectionType = request.args.get('conn_type')
        if connectionType == None:
            return 'conn_type key missing'
        rval = False
        if (connectionType == "telnet"):
            rval = telnet(hostname,username,password)

        if rval == True:
            resultArray.append({'variable':'returnAction','value':'Success','isRemove':True})
        else:
            resultArray.append({'variable':'returnAction','value':'Failure','isRemove':True})
        val = checkCondition1()

    elif actionType == "Run a Command":
        print ("run a command")
        try:
            if isOpen == True:
                logging.info("Id : %d - command - %s",reqNo,action["Command"])
                command = action["Command"]
                if (request.args.get('conn_type')== "telnet"):
                    user = bytes(request.args.get('username')+'\n', 'utf-8')
                    pass_word =bytes(request.args.get('password')+'\n', 'utf-8')
                    tillLogin = tn.read_until(b"login: ")
                    print (tillLogin)
                    tn.write(user)
                    tillPass = tn.read_until(b"Password: ")
                    print (tillPass)
                    tn.write(pass_word)
                    command_to_execute = bytes(command+'\n', 'utf-8')
                    testread = tn.read_until(b"$",5)
                    print (testread.decode('utf-8')[-1])
                    if (testread.decode('utf-8')[-1]!= '$'):
                        raise Exception("Login failed")
                    print ("writing command..")
                    tn.write(command_to_execute)
                    print ("command written")
                    #tn.write(b"exit\n")
                    commandbytes =bytes(command, 'utf-8') #converting string command to bytes
                    tillCommand = tn.read_until(commandbytes) #read till the command
                    print ("read till command",tillCommand)
                    nextline = tn.read_until(b"\n") #read till \n after the command
                    output = tn.read_until(bytes(request.args.get('username'), 'utf-8'))
                    print (output)
                    tn.write(b"exit\n")
                    t = output.decode("utf-8")
                    commandOutput = t[:t.rfind('\n')] #The rfind() method finds the last occurrence of the specified value.
                    print ("output is :",commandOutput)
                    errorTextArray = action["errorText"]
                    successTextArray = action["successText"]
                    isErrorTextFound = False
                    for text in errorTextArray:
                        if (isErrorTextFound == False and commandOutput.find(text['value'])!= -1):
                            isErrorTextFound = True
                    for text1 in successTextArray:
                        if (isErrorTextFound == False and commandOutput.find(text1['value'])== -1):
                            isErrorTextFound = True

                    if (isErrorTextFound):
                         resultArray.append({'variable':'returnAction','value':'Failure','isRemove':True})
                    else:
                        resultArray.append({'variable':'returnAction','value':'Success','isRemove':True})
                    val = checkCondition1()

            else:
                val = "No Connection"
        except Exception as e:
            print ("exception in run a command - ",str(e))
            val = str(e)

    elif actionType == "Parse the Output":
        print ("Parse output")
        
        try:
            editorDetail = mongo.db.EditorContent.find_one({'EditorId':action["EditorId"]})
            result = editorDetail["result"]
            #print commandOutput
            #print result
            if len(result)>0:
                #global resultArray
                #resultArray=[]
                for i in result:
                    
                    if i["condition"] == "Mark Position":
                        start = i["startPos"]
                        if i["endChar"] == "," or i["endChar"] ==";":
                            end = i["endPos"]
                        else:
                            end = i["endPos"]+1
                        lineNo = i["lineNo"]
                        resultLine = commandOutput.split('\n')[lineNo]
                        resultObj = {'variable':i["outputVar"],'value':resultLine[start:end],'isRemove':False}
                        resultArray.append(resultObj)
                        
                    elif i["condition"] == "Mark Text Same Line":
                        start = i["startPos"]
                        if i["endChar"] == "," or i["endChar"] ==";":
                            end = i["endPos"]
                        else:
                            end = i["endPos"]+1
                        searchString = i["text"][0]
                        #print ("searchString",searchString)
                        lines = commandOutput.count('\n')
                        n=0
                        
                        while n<lines:
                            selLine = commandOutput.split('\n')[n]
                            if selLine.find(searchString) != -1:
                                #print selLine
                                resultObj = {'variable':i["outputVar"],'value':selLine[start:end],'isRemove':False}
                                resultArray.append(resultObj)
                                break
                            else:
                                n+=1
                    elif i["condition"] == "Mark Text different Line|Position":
                        searchString = i["text"].strip()
                        #print searchString
                        lines = commandOutput.count('\n')
                        n=0
                        flag = False
                        while n<lines:
                            if flag == False:
                                selLine = commandOutput.split('\n')[n]
                                wordArray = selLine.split()
                                #print wordArray 
                                count = -1
                                for word in wordArray:
                                    count+=1
                                    if word == searchString:
                                        flag = True
                                        #print word,n  
                                        valueLine = commandOutput.split('\n')[n+1]
                                        #print valueLine
                                        wordArray1 = valueLine.split()
                                        #print wordArray1[count]
                                        resultObj = {'variable':i["outputVar"],'value':wordArray1[count],'isRemove':False}
                                        resultArray.append(resultObj)
                                        break                         
                            n+=1
                    
                    elif i["condition"] == "Mark Text different Line|Text":
                        start = i["index"][1]
                        if i["endChar"] == "," or i["endChar"] ==";":
                            end = i["index"][3]
                        else:
                            end = i["index"][3]+1
                        searchString = i["text"].strip()
                        #print searchString
                        lines = commandOutput.count('\n')
                        n=0
                        flag = False
                        while n<lines:
                            if flag == False:
                                selLine = commandOutput.split('\n')[n]
                                wordArray = selLine.split()
                                #print wordArray 
                                count=-1
                                for word in wordArray:
                                    count+=1
                                    if word == searchString:
                                        flag = True
                                        alignment=i["alignment"]
                                        selLine1 = commandOutput.split('\n')[n+1]
                                        
                                        
                                        if alignment == "left aligned":
                                            startLine = selLine[start:] # get the string from the start position of the first line
                                            startLineArray = startLine.split() #convert into array of words
                                            endIndex = selLine.find(startLineArray[1]) #get the index of the next word of the selected word which is the end index of the selected word
                                            #print endIndex
                                            wordValue = selLine1[start:endIndex]
                                            #getWord = selLine1[start:]
                                            #getWordArray = getWord.split()
                                            #resultObj = {'variable':i["outputVar"],'value':getWordArray[0]}
                                            resultObj = {'variable':i["outputVar"],'value':wordValue,'isRemove':False}
                                            resultArray.append(resultObj)
                                            break
                                        
                                        elif alignment == "right aligned":
                                            getWord = selLine1[:end]
                                            getWordArray = getWord.split()
                                            length = len(getWordArray)
                                            resultObj = {'variable':i["outputVar"],'value':getWordArray[length-1],'isRemove':False}
                                            resultArray.append(resultObj)
                                            break
                                        
                            n+=1
                    elif i["condition"] == "Mark Text as Block":
                        start = i["index"][1]
                        end = i["index"][3]+1
                        searchString = i["text"].strip()
                        #print searchString
                        lines = commandOutput.count('\n')
                        #print lines
                        n=0
                        flag = False
                        while n<lines:
                            if flag == False:
                                selLine = commandOutput.split('\n')[n]
                                wordArray = selLine.split()
                                #print wordArray 
                                count=-1
                                for word in wordArray:
                                    count+=1
                                    if word == searchString:
                                        flag = True
                                        getWordArray = []
                                        if i["endLine"] == "Not EOL":
                                            endLineValue = i["endLineValue"]
                                            #print ("endVal",endLineValue)
                                            stopIt = False
                                            for y in range(lines):
                                                if stopIt == False:
                                                    selLine2 = commandOutput.split('\n')[y]
                                                    #print selLine2
                                                    array = selLine2.split()
                                                    for word1 in array:
                                                        if word1 == endLineValue:
                                                            lines = y
                                                            stopIt=True

                                        for x in range(n+1,lines):
                                            selLine1 = commandOutput.split('\n')[x]
                                            getWord = selLine1[start:end]
                                            if getWord.isspace() == False:
                                                if getWord != "":
                                                    getWordArray.append(getWord)

                                        
                                        resultObj = {'variable':i["outputVar"],'value':getWordArray,'isRemove':False}
                                        resultArray.append(resultObj)
                                        
                                        break    
                                            
                            n+=1
                    elif i["condition"] == "Mark Text to Filter":
                        searchString = i["text"]
                        lines = commandOutput.count('\n')
                        filterText = i["filterText"].upper()
                        delimiter = i["delimiter"]
                        position = int(i["wordPosition"])
                        outOfRange = False
                        outputArray =[]
                        n=0
                        while n<lines:
                            selLine = commandOutput.split('\n')[n]
                            # if selLine.find(searchString)!= -1:
                            #     if selLine.upper().find(filterText)!= -1:
                            #         selArray = selLine.split(delimiter)
                            #         outputArray.append(selArray[position])
                            # if re.search(searchString,selLine):
                            #     if re.search(filterText,selLine):
                            #         selArray = selLine.split(delimiter)
                            #         outputArray.append(selArray[position])
                            flag = False
                            
                            wordArray = selLine.split()
                            for word in wordArray:
                                if word == searchString:
                                    flag = True
                                else:
                                    sepWordarray = word.split(',')
                                    for sepWord in sepWordarray:
                                        if sepWord == searchString:
                                            flag = True
                                if flag == True: #word is available
                                    for word1 in wordArray:
                                        if word1.upper() == filterText:
                                            selArray = selLine.split(delimiter)
                                            length = len(selArray)
                                            if position < length:
                                                outputArray.append(selArray[position])
                                            else:
                                                #outputArray=[]
                                                outputArray.append("word position out of range")
                                                outOfRange = True
                                                #break
                            n+=1
                        print (outputArray)
                        if outOfRange == False:
                            resultObj = {'variable':i["outputVar"],'value':outputArray,'isRemove':False}
                            resultArray.append(resultObj)
                        else:
                            resultObj = {'variable':i["outputVar"],'value':"out of range",'isRemove':False}
                            resultArray.append(resultObj)

                #print resultArray        
                        
            
            resultArray.append({'variable':'returnAction','value':"Success",'isRemove':True})
            val = checkCondition1()
        except Exception as e:
            val = "exception raised while parsing the output- "+str(e)
            
    return val


def telnet(hostname,username,password):
    global tn
    global isOpen
    try:
        #user = bytes(username+'\n', 'utf-8')
        #pass_word =bytes(password+'\n', 'utf-8')
        tn = telnetlib.Telnet(hostname)
        print ("telnet connection success")
        #tn.read_until(b"login: ")
        #tn.write(user)
        #tn.read_until(b"Password: ")
        #tn.write(pass_word)
        #print (tn.read_all())
        isOpen = True
        val = True
    except Exception as e:
        print ("telnet connection failed")
        print (str(e))
        val = False
    return val
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=13000)
