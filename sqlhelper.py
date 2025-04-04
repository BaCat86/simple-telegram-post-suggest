from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Boolean, String

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, unique=True, primary_key=True)
    is_admin = Column(Boolean)
    state = Column(Integer)

    def __init__(self, user_id, is_admin=False):
        self.user_id = user_id
        self.is_admin = is_admin

    def __repr__(self):
        return '<User(user_id={}, user_is_admin={})>'.format(self.user_id, self.is_admin)


class Post(Base):
    __tablename__ = 'posts'
    post_id = Column(Integer, unique=True, primary_key=True)
    owner_id = Column(Integer)
    attachment_path = Column(String)
    text = Column(String)
    owner_name = Column(String)
    file_type = Column(String)

    def __init__(self, owner_id, attachment_path, text, owner_name, file_type):
        self.owner_id = owner_id
        self.attachment_path = attachment_path
        self.text = text
        self.owner_name = owner_name
        self.file_type = file_type

    def __repr__(self):
        return '<Post(post_id={}, owner_id={}, attachment_filename={}, text={}, owner_name={}, file_type={}>'.format(self.post_id,
                                                                                        self.owner_id,
                                                                                        self.attachment_path,
                                                                                        self.text,
                                                                                        self.owner_name,
                                                                                        self.file_type)


class Settings(Base):
    __tablename__ = 'settings'
    initialized = Column(Boolean, unique=True, primary_key=True)
    target_channel = Column(String)
    initializer_id = Column(Integer)

    def __init__(self, initialized, target_channel, initializer_id):
        self.initialized = initialized
        self.target_channel = target_channel
        self.initializer_id = initializer_id

    def __repr__(self):
        return '<Settings(initialized={}, target_channel={}, initializer_id={})>'.format(self.initialized,
                                                                                        self.target_channel,
                                                                                        self.initializer_id)
