from sqlalchemy.orm import Session


class BaseRepository: # base class for all repositories, accepts an injected SQLAlchemy session

    def __init__(self, session: Session):
        self.session = session
