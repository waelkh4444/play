# Utiliser une image Python légère
FROM python:3.11-slim

# Éviter les caches inutiles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Installer les dépendances système minimales requises pour Playwright Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    ca-certificates \
    fonts-liberation \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    libxext6 \
    libxi6 \
    libgtk-3-0 \
    libdbus-1-3 \
    libasound2 \
    xdg-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Définir le dossier de travail
WORKDIR /app

# Copier les fichiers du projet
COPY . /app

# Installer pip et les dépendances Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Télécharger les navigateurs Playwright nécessaires
RUN playwright install --with-deps

# Exposer le port de l'app Flask (ou FastAPI)
EXPOSE 5000

# Commande pour démarrer l’application avec gunicorn
CMD ["gunicorn", "scraping:app", "--bind", "0.0.0.0:5000", "--timeout", "180"]
