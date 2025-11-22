#!/bin/bash
echo "Criando ambiente Python..."
python3 -m venv videoenv
echo "Ativando venv..."
source videoenv/bin/activate
echo "Instalando as dependências..."
pip install -r requirements.txt
deactivate
echo "Instalando os aplicativos..."
mv shorts.py $HOME/.local/bin/shorts
chmod +x $HOME/.local/bin/shorts
mv quiz.py $HOME/.local/bin/quiz
chmod +x $HOME/.local/bin/quiz
mv videoenv $HOME/.local/share/videoenv -rf
mv quiz.zip $HOME/Modelos/quiz.zip

echo "Instalado com sucesso. Pode gerar seus vídeos e ganhar muito dinheiro!"


