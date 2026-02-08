from sqlalchemy import select

from app.db.models import t_impression
from app.db.session import get_session


def main():
    with get_session() as session:
        rows = session.execute(select(t_impression).limit(5)).fetchall()

        for row in rows:
            print(row)

        print(f"\nTotal rows returned: {len(rows)}")


if __name__ == "__main__":
    main()
