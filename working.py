# load the evaluation libraries
# the LIGSITE_csc

from Bio import PDB
import os.path
import re
import json
import os
from shutil import copyfile, rmtree
from flask import Flask, render_template, request, jsonify


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

        if not overrideAll and os.path.isfile(failedDownloadsLogFile):
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
                self.downloadFailed.add(pdbID)
                print "Failed to download", pdbID

        failedLog = open(failedDownloadsLogFile, 'w')
        failedLog.write(json.dumps(list(self.downloadFailed)))


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

    pdbLoader = None
    outputFolder = ""
    executionString = ""

    def __init__(self, pdbLoader, outputFolder):
        self.outputFolder = outputFolder
        self.pdbLoader = pdbLoader

    def makeExecCommand(self, user_input):
        print user_input
        print self.executionString
        return self.executionString % user_input

    def run_all(self):
        for i in range(len(self.pdbLoader.files)):
            self.pdbLoader[i].getStructure()
            self.run_one(self.pdbLoader[i])

    def run_one(self, structure):
        try:
            os.system(self.makeExecCommand(structure.fileName))
        except:
            print self.makeExecCommand(structure.fileName) + "FAILED TO EXECUTE"
            raise


class Ligsite (PredictionAlgorithm):

    pdbParser = PDB.PDBParser(PERMISSIVE=1)

    def __init__(self, pdbLoader, outputFolder):
        self.executionString = "./algo/lcs -i %s"
        PredictionAlgorithm.__init__(self, pdbLoader, outputFolder)

    def run_one(self, structure):
        os.environ['LD_LIBRARY_PATH'] = './algo'
        PredictionAlgorithm.run_one(self, structure)

        # cleanup
        try:
            copyfile(structure.fileName, self.outputFolder + "/" + structure.pdbID + ".pdb")
        except:
            pass

            os.rename("pocket.pdb", self.outputFolder + "/" + structure.pdbID + "_best.pdb")
            os.rename("pocket_all.pdb", self.outputFolder + "/" + structure.pdbID + "_clusters.pdb")
            os.rename("pocket_r.pdb", self.outputFolder + "/" + structure.pdbID + "_all.pdb")
            os.remove("pocket.py")


def tryMove(fro, to):
    try:
        os.rename(fro, to)
    except (IOError, OSError):
        pass


class PASS(PredictionAlgorithm):
    pdbParser = PDB.PDBParser(PERMISSIVE=1)

    def __init__(self, pdbLoader, outputFolder):
        self.executionString = "./algo/pass %s"
        PredictionAlgorithm.__init__(self, pdbLoader, outputFolder)

    def run_one(self, structure):
        PredictionAlgorithm.run_one(self, structure)
        print structure.pdbID + "_asps.pdb"
        # cleanup
        # TODO: test whether the files is present...
        try:
            copyfile(structure.fileName, self.outputFolder + "/" + structure.pdbID + ".pdb")
        except:
            pass
        try:
            tryMove(structure.pdbID + "_asps.pdb", self.outputFolder + "/" + structure.pdbID + "_asps.pdb")
            tryMove(structure.pdbID + "_lig1.pdb", self.outputFolder + "/" + structure.pdbID + "_lig1.pdb")
            tryMove(structure.pdbID + "_lig2.pdb", self.outputFolder + "/" + structure.pdbID + "_lig2.pdb")
            tryMove(structure.pdbID + "_lig3.pdb", self.outputFolder + "/" + structure.pdbID + "_lig3.pdb")
            tryMove(structure.pdbID + "_probes.pdb", self.outputFolder + "/" + structure.pdbID + "_probes.pdb")
        except:
            pass

# pdbLoader2 = PDBLoader(directory="static/pdbs/")
# algorithmRunner = PASS(pdbLoader2, outputFolder="static/pdbs/")
# algorithmRunner.run_all()


def generateDatabase(toDownload, downloadDirectory, outputDirectory):
    structureDownloader = PDBDownloader(downloadDirectory=downloadDirectory)
    structureDownloader.download(pdbIDList=toDownload, overrideAll=False)
    pdbLoader = PDBLoader(directory=downloadDirectory)
    LigsiteCS = PredictionAlgorithm(pdbLoader, outputFolder=outputDirectory)
    LigsiteCS.run_all()

# generateDatabase(["1eyz", "1r6a", "1rb8"], "static/PDBRaw", "static/pdbs/")

# Visualization server

app = Flask(__name__, static_url_path='/static')


@app.route('/<name>')
def renderStructure(name=None):
    return render_template('viewer.html', name=name)


@app.route('/request', methods=['POST', 'GET'])
def handleRequest():
    print "Handling request"
    if request.method == 'GET':
        return jsonify("Error")
    else:
        structureDownloader = PDBDownloader(downloadDirectory="tmp")
        structureDownloader.download(pdbIDList=[request.form["id"]], overrideAll=False)
        pdbLoader = PDBLoader(directory="tmp")
        run_ligsite = Ligsite(pdbLoader, outputFolder="static/pdbs/")
        run_pass = PASS(pdbLoader, outputFolder="static/pdbs/")
        run_ligsite.run_all()
        run_pass.run_all()
        rmtree("tmp", ignore_errors=True)
        return render_template('viewer.html', name=request.form["id"])


@app.route('/', methods=['POST', 'GET'])
def bootstrap():
    return render_template('index.html')


@app.route('/add')
def add():
    return render_template('add.html')


@app.route('/_get_downloaded')
def getDownloaded():
    return jsonify(result=list(PDBLoader(directory="static/pdbs").getPDBIDs()))
