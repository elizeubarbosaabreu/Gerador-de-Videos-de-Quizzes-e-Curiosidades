#!/ bin/bash
echo "Criando ambiente Python..."
python3 -m venv videoenv
echo "Ativando venv..."
source videoenv/bin/activate
echo "Instalando as dependências..."
pip install -r requirements.txt
deactivate
echo "Instalando os aplicativos..."
mv shorts.py ~/.local/bin/shorts
chmod +x ~/.local/bin/shorts
mv quiz.py ~/.local/bin/quiz
chmod +x ~/.local/bin/quiz
mv videoenv ~/.local/share/videoenv -rf
mv quiz.zip $HOME/Modelos/quiz.zip

echo "Instalado com sucesso. POde gerar seus vídeos e ganhar muito dinheiro!"


