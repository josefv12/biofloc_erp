from pydantic import BaseModel

class LoginRequest(BaseModel):
    correo: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    nombre: str
    correo: str
    rol: str
    activo: bool

    class Config:
        from_attributes = True
