import subprocess
from Bio import PDB
import os.path
import re
import json
import os
from shutil import rmtree
import zipfile
from flask import Flask, render_template, request, jsonify
import requests
import StringIO
import time

class PDBDownloader:
    downloadFailed = set()
    downloadSkipped = []
    downloadSuccessful = []

    downloadDirectory = ""

    def __init__(self, downloadDirectory="PDB"):
        self.downloadDirectory = downloadDirectory

    def _getNameFromPdbID(self, pdbID):
        return self.downloadDirectory + "/" + pdbID + ".pdb"

    def download(self, pdbIDList, overrideAll=False):
        """
        Download PDB files from ftp://ftp.wwpdb.org

        :param pdbIDList: list of structures to download
        :param overrideAll: Overrides all already downloaded files if set to True
        :return: None
        """
        pdbList = PDB.PDBList()
        failedDownloadsLogFile = self.downloadDirectory + "/failedLog"

        if not os.path.exists(self.downloadDirectory):
            os.makedirs(self.downloadDirectory)
        if not overrideAll and os.path.exists(failedDownloadsLogFile):
            failedLog = open(failedDownloadsLogFile, 'r')
            try:
                self.downloadFailed = self.downloadFailed.union(json.load(failedLog))
            except:
                print "no FailLog detected"
                pass
            failedLog.close()

        for pdbID in set(pdbIDList) - self.downloadFailed:
            if not overrideAll:
                if os.path.exists(self._getNameFromPdbID(pdbID)):
                    self.downloadSkipped.append(pdbID)
                    continue

            try:
                dl_name = pdbList.retrieve_pdb_file(pdbID, pdir=self.downloadDirectory)
                os.rename(dl_name, self.downloadDirectory+"/"+pdbID + ".pdb")
                self.downloadSuccessful.append(pdbID)
                print "Downloaded", pdbID
            except IOError:
                #self.downloadFailed.add(pdbID)
                print "Failed to download", pdbID
        # TODO: napisat normalny manager
        try:
            failedLog = open(failedDownloadsLogFile, 'w')
            failedLog.write(json.dumps(list(self.downloadFailed)))
        except:
            pass

class PDBLoader:
    directory = ""
    files = []

    def _getPdbFromName(self, name):
        return name.split(".")[-2][-4:]

    def getPDBIDs(self):
        for fileName in self.files:
            yield self._getPdbFromName(fileName)

    def _checkIfIsPDBFile(self, fileName):
        return re.match('.*(pdb){0,1}[0-9][a-zA-Z0-9]{3}\.(pdb|PDB|ent|ENT)', fileName) is not None

    def __init__(self, directory="PDB"):
        self.files = []
        self.directory = directory[:]
        for fileName in os.listdir(directory):
            if self._checkIfIsPDBFile(fileName):
                self.files.append(fileName)

    def printFiles(self):
        print "Printing files in folder", self.directory
        for fileName in self.files:
            print fileName

    def nameToStructure(self, item):
        return ProteinStructure(self._getPdbFromName(item), self.directory + "/" + item)

    def __getitem__(self, item):
        if isinstance(item, int):
            return ProteinStructure(self._getPdbFromName(self.files[item]), self.directory + "/" + self.files[item])

    def __iter__(self):
        return iter(self.files)


class ProteinStructure:
    pdbID = ""
    fileName = ""

    pdbParser = PDB.PDBParser()

    def __init__(self, pdbID, path):
        self.fileName = path
        self.pdbID = pdbID

    def getStructure(self):
        self.pdbParser.get_structure(self.pdbID, self.fileName)


class PredictionAlgorithm:
    pdbParser = PDB.PDBParser(PERMISSIVE=1)

    outputFolder = ""
    executionString = ""
    structure = ""
    mapping = {}
    ZIP_DESTINATION = ""

    def __init__(self, outputFolder, structure=None):
        if structure:
            self.outputFolder = outputFolder
            self.structure = structure

    def makeExecCommand(self, user_input):
        print user_input
        print self.executionString
        return self.executionString % user_input

    def run(self):
        try:
            os.system(self.makeExecCommand(self.structure.fileName))
        except:
            print self.makeExecCommand(self.structure.fileName) + "FAILED TO EXECUTE"
            raise

        self.deploy()

    def deploy(self):
        try:
            zf = zipfile.ZipFile('static/' + self.ZIP_DESTINATION, mode='w')
            for (source, destination) in self.mapping.items():
                if not destination == "":
                    zf.write(source, destination)

            zf.close()

            for source in self.mapping.keys():
                os.remove(source)
        except:
            pass

    # TODO: ak je file v databaze dbLoader uz ho nestahujeme
    def getPDBandRun(self, pdbID, dbLoader = None):
        structureDownloader = PDBDownloader(downloadDirectory="tmp")
        structureDownloader.download(pdbIDList=[pdbID], overrideAll=True)
        pdbLoader = PDBLoader(directory="tmp")
        self.structure = pdbLoader.nameToStructure(pdbLoader.files[0])
        try:
            self.run()
        except:
            print "EXECUTION FAILED"
            raise
        rmtree("tmp", ignore_errors=True)


app = Flask(__name__, static_url_path='/static')


@app.route('/', methods=['POST', 'GET'])
def bootstrap():
    return render_template('index.html')


@app.route('/_get_downloaded')
def getDownloaded():
    return jsonify(result=list(PDBLoader(directory="static/pdbs").getPDBIDs()))


services = {
    "PASS": {
        "url": "http://0.0.0.0:7010",
        "script": "pass_server.py"
    },

    "Ligsite": {
        "url": "http://0.0.0.0:7012",
        "script": "ligsite_server.py"
    }
}

registeredServices = {}


@app.route('/request', methods=['POST', 'GET'])
def handleRequest():
    print "Handling request"
    if request.method == 'GET':
        return jsonify("Error")
    else:
        for (name, data) in services.items():
            print "serving " + name
            print(repr(data["url"]))
            r = requests.get(data["url"]+"/"+request.form["id"])
            z = zipfile.ZipFile(StringIO.StringIO(r.content))
            z.extractall("static/pdbs/")

        return render_template('viewer.html', name=request.form["id"])


# @app.route('/register_service/<id>')
# def registerService(idp=None):
#    idp = idp.split("_")
#    registeredServices[idp[0]] = idp[1]
#    print "register", idp[0], idp[1]
#    return 200


def waitForServiceRegistration():
    registeredServices = {}

    while not len(registeredServices) == len(services):
        with open("register.txt") as f:
            for line in f.readlines():
                idp = line.strip().split(":")
                registeredServices[idp[0]] = idp[1]
        time.sleep(0.5)

    for (name, port) in registeredServices.items():
        services[name]["url"] = "http://0.0.0.0:" + port
    print services


if __name__ == "__main__":
    f = open("register.txt", "w")
    f.close()
    for service in services.values():
        p = subprocess.Popen(["python", service["script"]])

    waitForServiceRegistration()

    app.run(host='0.0.0.0', port=7100, debug=False)
