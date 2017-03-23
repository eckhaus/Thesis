from abstract_prediction_server import *
import socket


class Ligsite (PredictionAlgorithm):
    pdbParser = PDB.PDBParser(PERMISSIVE=1)

    def __init__(self, outputFolder, structure=None):
        self.executionString = "~/thesis/algo/lcs -i %s"
        PredictionAlgorithm.__init__(self, outputFolder, structure)

    def run(self):
        os.system("export LD_LIBRARY_PATH=~/thesis/algo")
        PredictionAlgorithm.run(self)

    def deploy(self):
        self.ZIP_DESTINATION = "run.zip"
        self.mapping = {
            "pocket.pdb": self.structure.pdbID + "_best.pdb",
            "pocket_all.pdb": self.structure.pdbID + "_clusters.pdb",
            "pocket_r.pdb": self.structure.pdbID + "_all.pdb",
            "pocket.py": ""
        }

        PredictionAlgorithm.deploy(self)


app = Flask(__name__, static_url_path='/static')


@app.route('/<name>', methods=['POST', 'GET'])
def handleRequest(name=None):
    Ligsite(outputFolder="static/ligsite/").getPDBandRun(name)
    return app.send_static_file('run.zip')


def register(p):

    f = open("register.txt", "a")
    #requests.get('http://0.0.0.0:7100/register_service/Ligsite:' + str(f))
    f.write('Ligsite:' + str(p) + "\n")
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
