
echo "Installing Docker ...."
bash ${PWD}/installdocker.sh

docker build -t orquesta .


docker run -it -d --name orequesta -p 5000:5000 orquesta


echo "Now open browser with url as: hostip:5000"
