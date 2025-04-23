from func.models.database import database
from func.utils import generate_unique_id

class Interest:
    def __init__(self, id: str, name: str, description: str = None):
        self.id = id
        self.name = name
        self.description = description

    def __repr__(self):
        return f"Interest(id={self.id}, name={self.name}, description={self.description})"
    
    def __eq__(self, value):
        if isinstance(value, Interest):
            return self.id == value.id
        return False
    
    @classmethod
    def get(cls, id: str = None, name: str = None):
        if id is None and name is None:
            raise ValueError("Either id or name must be provided")
        
        query = None
        params = ()

        if id is not None:
            query = "SELECT * FROM interests WHERE id = ?"
            params = (id,)
        elif name is not None:
            query = "SELECT * FROM interests WHERE name = ?"
            params = (name,)

        result = database.select(query, params, limit=1)
        if result:
            return cls(id=result['id'], name=result['name'], description=result['description'])
        return None

    @classmethod
    def create(cls, name: str, description: str = None):
        if not name:
            raise ValueError("Name cannot be empty")
        
        # Check if the interest already exists
        existing_interest = cls.get(name=name)
        if existing_interest:
            return existing_interest

        id = generate_unique_id()
        interest = cls(id=id, name=name, description=description)
        return interest.save(insert=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }
    
    def save(self, insert: bool = False):
        query = None
        params = ()

        if insert:
            query = "INSERT INTO interests (id, name, description) VALUES (?, ?, ?)"
            params = (self.id, self.name, self.description)
        else:
            query = "UPDATE interests SET name = ?, description = ? WHERE id = ?"
            params = (self.name, self.description, self.id)

        database.query(query, params)
        return self