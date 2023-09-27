import server
import model
from helpers import *

# Delete the existing database if it exists
os.system('rm pt_database.db')

model.connect_to_db(server.app)
model.db.create_all()


if __name__ == '__main__':
    print("Database initialisation completed.")
