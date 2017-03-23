sudo docker stop flask_cont
sudo docker rm flask_cont
sudo docker run --name flask_cont eckhaus/flask > /dev/null 2>&1 &

