from abstract_prediction_server import *
import glob
import socket

class PASS(PredictionAlgorithm):
    pdbParser = PDB.PDBParser(PERMISSIVE=1)

    def __init__(self, outputFolder, structure=None):
        self.executionString = "./algo/pass %s"
        PredictionAlgorithm.__init__(self, outputFolder, structure)

    def deploy(self):
        self.ZIP_DESTINATION = "run.zip"
        # self.structure is not defined before deployment
        self.mapping = {
            self.structure.pdbID + "_asps.pdb": self.structure.pdbID + "_asps.pdb",
            self.structure.pdbID + "_probes.pdb": self.structure.pdbID + "_probes.pdb",
            self.structure.fileName: self.structure.pdbID + ".pdb"
        }

        for lig in glob.glob(self.structure.pdbID + "_lig*.pdb"):
            self.mapping[lig] = lig
        PredictionAlgorithm.deploy(self)

app = Flask(__name__, static_url_path='/static')


@app.route('/<name>', methods=['POST', 'GET'])
def handleRequest(name=None):
    PASS(outputFolder="static/pass/").getPDBandRun(name)
    return app.send_static_file('run.zip')


def register(p):
    f = open("register.txt", "a")
    #requests.get('http://0.0.0.0:7100/register_service/PASS:' + str(f))
    f.write('PASS:' + str(p) + "\n")
    f.close()

if __name__ == "__main__":
    def get_free_port():
        s = socket.socket()
        s.bind(('', 0))
        free_port = s.getsockname()[1]
        s.close()
        return free_port

    probablyFreePort = get_free_port()
    register(probablyFreePort)
    app.run(host='0.0.0.0', port=probablyFreePort, debug=False)
