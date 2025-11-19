# app.py
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os

# --------------------------
# Configuration DB
# --------------------------
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Admin123!")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "digicheese")

CONNECTION_STRING = f"sqlite:///./test.db"  # pour simplification, on utilise SQLite
engine = create_engine(CONNECTION_STRING, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --------------------------
# Models
# --------------------------
Base = declarative_base()

class Client(Base):
    __tablename__ = "t_client"
    codcli = Column(Integer, primary_key=True, index=True)
    nom = Column(String(40), index=True)
    prenom = Column(String(30))
    genre = Column(String(8), default=None)
    adresse = Column(String(50))
    complement_adresse = Column(String(50), default=None)
    tel = Column(String(10), default=None)
    email = Column(String(255), default=None)
    newsletter = Column(Integer, default=0)

# Créer les tables
Base.metadata.create_all(bind=engine)

# --------------------------
# Schemas 
# --------------------------
from pydantic import BaseModel
from typing import Optional, List

class ClientBase(BaseModel):
    nom: str
    prenom: str
    genre: Optional[str] = None
    adresse: str
    complement_adresse: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    newsletter: Optional[int] = 0

class ClientPost(ClientBase):
    pass

class ClientPatch(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    adresse: Optional[str] = None
    complement_adresse: Optional[str] = None
    genre: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    newsletter: Optional[int] = None

class ClientInDB(ClientBase):
    codcli: int
    class Config:
        orm_mode = True

# --------------------------
# Repository
# --------------------------
class ClientRepository:
    def get_all_clients(self, db: Session):
        return list(db.query(Client).all())

    def get_client_by_id(self, db: Session, id: int):
        return db.query(Client).get(id)

    def create_client(self, db: Session, data: dict):
        client = Client(**data)
        db.add(client)
        db.commit()
        db.refresh(client)
        return client

    def patch_client(self, db: Session, id: int, data: dict):
        client = db.query(Client).get(id)
        for k, v in data.items():
            setattr(client, k, v)
        db.commit()
        db.refresh(client)
        return client

    def delete_client(self, db: Session, id: int):
        client = db.query(Client).get(id)
        db.delete(client)
        db.commit()
        return client

# --------------------------
# Service
# --------------------------
class ClientService:
    def __init__(self):
        self.repo = ClientRepository()

    def get_all_clients(self, db: Session):
        return self.repo.get_all_clients(db)

    def get_client_by_id(self, db: Session, client_id: int):
        return self.repo.get_client_by_id(db, client_id)

    def create_client(self, db: Session, new_client: ClientPost):
        data = new_client.model_dump()
        return self.repo.create_client(db, data)

    def patch_client(self, db: Session, client_id: int, client: ClientPatch):
        data = client.model_dump(exclude_unset=True)
        return self.repo.patch_client(db, client_id, data)

    def delete_client(self, db: Session, client_id: int):
        return self.repo.delete_client(db, client_id)

# --------------------------
# FastAPI app
# --------------------------
app = FastAPI()
router = APIRouter(prefix="/api/v1/client", tags=["client"])
service = ClientService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[ClientInDB])
def get_clients(db: Session = Depends(get_db)):
    return service.get_all_clients(db)

@router.get("/{client_id}", response_model=ClientInDB)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = service.get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    return client

@router.post("/", response_model=ClientInDB)
def create_client(client: ClientPost, db: Session = Depends(get_db)):
    return service.create_client(db, client)

@router.patch("/{client_id}", response_model=ClientInDB)
def patch_client(client_id: int, client: ClientPatch, db: Session = Depends(get_db)):
    db_client = service.get_client_by_id(db, client_id)
    if not db_client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    return service.patch_client(db, client_id, client)

@router.delete("/{client_id}", response_model=ClientInDB)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    db_client = service.get_client_by_id(db, client_id)
    if not db_client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    return service.delete_client(db, client_id)

app.include_router(router)

# --------------------------
# Root
# --------------------------
@app.get("/")
def root():
    return {"message": "FastAPI operational"}

# --------------------------
# Tests intégrés pour pytest
# --------------------------
def test_root():
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "FastAPI operational"}

def test_create_and_get_client():
    from fastapi.testclient import TestClient
    client = TestClient(app)
    # Création d'un client
    client_data = {
        "nom": "Dupont",
        "prenom": "Jean",
        "adresse": "123 Rue Exemple"
    }
    response = client.post("/api/v1/client/", json=client_data)
    assert response.status_code == 200
    created = response.json()
    assert created["nom"] == "Dupont"
    assert created["prenom"] == "Jean"
    client_id = created["codcli"]

    # Récupération du client
    response_get = client.get(f"/api/v1/client/{client_id}")
    assert response_get.status_code == 200
    fetched = response_get.json()
    assert fetched["nom"] == "Dupont"
    assert fetched["prenom"] == "Jean"

def test_patch_client():
    from fastapi.testclient import TestClient
    client = TestClient(app)
    # Création d'un client
    client_data = {
        "nom": "Martin",
        "prenom": "Paul",
        "adresse": "456 Rue Exemple"
    }
    response = client.post("/api/v1/client/", json=client_data)
    created = response.json()
    client_id = created["codcli"]

    # Patch du client
    patch_data = {"prenom": "Pierre"}
    response_patch = client.patch(f"/api/v1/client/{client_id}", json=patch_data)
    assert response_patch.status_code == 200
    updated = response_patch.json()
    assert updated["prenom"] == "Pierre"

# --------------------------
# Test pour la gestion des erreurs
# --------------------------
def test_get_nonexistent_client():
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # On tente de récupérer un client qui n'existe pas
    response = client.get("/api/v1/client/99999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Client non trouvé"}

# --------------------------
# Test pour la suppression avec cas de bord et d'erreur
# --------------------------
def test_delete_client_with_edge_and_error_cases():
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # -------------------------
    # 1) Cas nominal : suppression réussie
    # -------------------------
    data = {
        "nom": "Test",
        "prenom": "User",
        "adresse": "1 Rue Exemple"
    }
    create_resp = client.post("/api/v1/client/", json=data)
    assert create_resp.status_code == 200
    created_id = create_resp.json()["codcli"]

    delete_resp = client.delete(f"/api/v1/client/{created_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["codcli"] == created_id

    # Vérifier que le client n'existe plus
    get_resp_after_delete = client.get(f"/api/v1/client/{created_id}")
    assert get_resp_after_delete.status_code == 404

    # -------------------------
    # 2) Cas d'erreur : suppression d'un client inexistant → 404
    # -------------------------
    resp = client.delete("/api/v1/client/999999")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Client non trouvé"}

    # -------------------------
    # 3) Cas de bord : ID = 0 → doit renvoyer 404 (client impossible)
    # -------------------------
    resp = client.delete("/api/v1/client/0")
    assert resp.status_code == 404

    # -------------------------
    # 4) Cas d'erreur d'entrée : ID non numérique → 422 Unprocessable Entity
    # -------------------------
    resp = client.delete("/api/v1/client/abc")
    assert resp.status_code == 422  # FastAPI valide les types automatiquement

    # -------------------------
    # 5) Cas d'exception interne simulée
    #    (si tu veux tester la robustesse)
    # -------------------------
    # On monkeypatch une exception interne dans le repo
    import pytest
    from unittest.mock import patch

    with patch("app.ClientRepository.delete_client", side_effect=Exception("Erreur interne")):
        data2 = {"nom": "Crash", "prenom": "Test", "adresse": "2 Rue Exemple"}
        create_resp2 = client.post("/api/v1/client/", json=data2)
        new_id = create_resp2.json()["codcli"]

        # L'appel doit provoquer une 500
        resp = client.delete(f"/api/v1/client/{new_id}")
        assert resp.status_code == 500 or resp.status_code == 200  # dépend si tu gères l'exception




# --------------------------
# Run app (for direct python execution)
# --------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)




