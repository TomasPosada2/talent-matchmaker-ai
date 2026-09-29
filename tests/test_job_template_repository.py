from src import job_template_repository


class CursorFake:
    def __init__(
        self,
        fetchone_result=None,
        fetchall_result=None,
    ):
        self.fetchone_result = fetchone_result
        self.fetchall_result = fetchall_result or []
        self.consulta = None
        self.parametros = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, consulta, parametros=None):
        self.consulta = consulta
        self.parametros = parametros

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return self.fetchall_result


class ConexionFake:
    def __init__(self, cursor):
        self.cursor_fake = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def cursor(self, *args, **kwargs):
        return self.cursor_fake


def test_crear_tabla(monkeypatch):
    cursor = CursorFake()
    conexion = ConexionFake(cursor)

    monkeypatch.setattr(
        job_template_repository.profile_repository,
        "obtener_conexion",
        lambda: conexion,
    )

    job_template_repository.crear_tabla()

    assert "CREATE TABLE IF NOT EXISTS job_templates" in (
        cursor.consulta
    )
    assert "REFERENCES recruiters(id)" in cursor.consulta


def test_guardar_plantilla(monkeypatch):
    fila = {
        "id": 1,
        "recruiter_id": 10,
        "nombre": "Backend Developer",
        "vacante": {
            "titulo": "Backend Developer",
            "experiencia": "3 años",
        },
    }

    cursor = CursorFake(
        fetchone_result=fila,
    )
    conexion = ConexionFake(cursor)

    monkeypatch.setattr(
        job_template_repository.profile_repository,
        "obtener_conexion",
        lambda: conexion,
    )

    resultado = job_template_repository.guardar_plantilla(
        recruiter_id=10,
        nombre="Backend Developer",
        vacante={
            "titulo": "Backend Developer",
            "experiencia": "3 años",
        },
    )

    assert resultado == fila
    assert cursor.parametros[0] == 10
    assert cursor.parametros[1] == "Backend Developer"
    assert "Backend Developer" in cursor.parametros[2]


def test_guardar_plantilla_actualiza_si_existe(
    monkeypatch,
):
    cursor = CursorFake(
        fetchone_result={
            "id": 1,
            "recruiter_id": 10,
            "nombre": "Backend Developer",
            "vacante": {
                "titulo": "Backend Developer Senior",
            },
        }
    )
    conexion = ConexionFake(cursor)

    monkeypatch.setattr(
        job_template_repository.profile_repository,
        "obtener_conexion",
        lambda: conexion,
    )

    job_template_repository.guardar_plantilla(
        recruiter_id=10,
        nombre="Backend Developer",
        vacante={
            "titulo": "Backend Developer Senior",
        },
    )

    assert "ON CONFLICT" in cursor.consulta
    assert "DO UPDATE" in cursor.consulta


def test_listar_plantillas(monkeypatch):
    filas = [
        {
            "id": 1,
            "recruiter_id": 10,
            "nombre": "Backend",
            "vacante": {
                "titulo": "Backend Developer",
            },
        },
        {
            "id": 2,
            "recruiter_id": 10,
            "nombre": "Data",
            "vacante": {
                "titulo": "Data Engineer",
            },
        },
    ]

    cursor = CursorFake(
        fetchall_result=filas,
    )
    conexion = ConexionFake(cursor)

    monkeypatch.setattr(
        job_template_repository.profile_repository,
        "obtener_conexion",
        lambda: conexion,
    )

    resultado = job_template_repository.listar_plantillas(
        recruiter_id=10,
    )

    assert resultado == filas
    assert cursor.parametros == (10,)


def test_obtener_plantilla(monkeypatch):
    fila = {
        "id": 7,
        "recruiter_id": 10,
        "nombre": "Backend",
        "vacante": {
            "titulo": "Backend Developer",
        },
    }

    cursor = CursorFake(
        fetchone_result=fila,
    )
    conexion = ConexionFake(cursor)

    monkeypatch.setattr(
        job_template_repository.profile_repository,
        "obtener_conexion",
        lambda: conexion,
    )

    resultado = job_template_repository.obtener_plantilla(
        recruiter_id=10,
        template_id=7,
    )

    assert resultado == fila
    assert cursor.parametros == (7, 10)


def test_obtener_plantilla_no_encontrada(monkeypatch):
    cursor = CursorFake(
        fetchone_result=None,
    )
    conexion = ConexionFake(cursor)

    monkeypatch.setattr(
        job_template_repository.profile_repository,
        "obtener_conexion",
        lambda: conexion,
    )

    resultado = job_template_repository.obtener_plantilla(
        recruiter_id=10,
        template_id=999,
    )

    assert resultado is None


def test_plantillas_filtradas_por_recruiter(
    monkeypatch,
):
    cursor = CursorFake(
        fetchall_result=[],
    )
    conexion = ConexionFake(cursor)

    monkeypatch.setattr(
        job_template_repository.profile_repository,
        "obtener_conexion",
        lambda: conexion,
    )

    job_template_repository.listar_plantillas(
        recruiter_id=25,
    )

    assert "WHERE recruiter_id = %s" in cursor.consulta
    assert cursor.parametros == (25,)