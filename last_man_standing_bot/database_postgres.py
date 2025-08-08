import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

Base = declarative_base()

# SQLAlchemy Models
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Pick(Base):
    __tablename__ = 'picks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    round_number = Column(Integer, nullable=False)
    team_name = Column(String(255), nullable=False)
    team_id = Column(Integer)
    result = Column(String(50))
    chat_id = Column(BigInteger, nullable=False)
    competition_id = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class Group(Base):
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, unique=True, nullable=False)
    chat_title = Column(String(255))
    chat_type = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Winner(Base):
    __tablename__ = 'winners'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    chat_id = Column(Integer, nullable=False)
    competition_id = Column(Integer, default=1)
    won_at = Column(DateTime, default=datetime.utcnow)

class Competition(Base):
    __tablename__ = 'competitions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Rollover(Base):
    __tablename__ = 'rollovers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False)
    count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class GroupMember(Base):
    __tablename__ = 'group_members'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

class DatabasePostgres:
    def __init__(self):
        # Use PostgreSQL if DATABASE_URL is set (Render), otherwise SQLite for local dev
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # PostgreSQL on Render
            # Fix for Render's postgres:// URL (SQLAlchemy needs postgresql://)
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            self.engine = create_engine(database_url)
            logger.info("Connected to PostgreSQL database")
        else:
            # SQLite for local development
            self.engine = create_engine('sqlite:///lastman.db')
            logger.info("Connected to SQLite database (local development)")
        
        self.Session = sessionmaker(bind=self.engine)
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add a new user to the database"""
        session = self.Session()
        try:
            # Check if user already exists
            existing_user = session.query(User).filter_by(user_id=user_id).first()
            if existing_user:
                # Update user info if it exists
                existing_user.username = username
                existing_user.first_name = first_name
                existing_user.last_name = last_name
                existing_user.is_active = True
            else:
                # Create new user
                new_user = User(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(new_user)
            
            session.commit()
            logger.info(f"User {user_id} added/updated successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding user {user_id}: {e}")
        finally:
            session.close()
    
    def add_user_to_group(self, user_id: int, chat_id: int):
        """Add a user to a specific group"""
        session = self.Session()
        try:
            # Check if user is already in this group
            existing_member = session.query(GroupMember).filter_by(
                user_id=user_id, 
                chat_id=chat_id
            ).first()
            
            if existing_member:
                # Reactivate if they were previously eliminated
                existing_member.is_active = True
            else:
                # Add user to group
                new_member = GroupMember(
                    user_id=user_id,
                    chat_id=chat_id,
                    is_active=True
                )
                session.add(new_member)
            
            session.commit()
            logger.info(f"User {user_id} added to group {chat_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding user {user_id} to group {chat_id}: {e}")
        finally:
            session.close()
    
    def get_user(self, user_id: int):
        """Get user by user_id"""
        session = self.Session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()
            if user:
                return (user.user_id, user.username, user.first_name, user.last_name)
            return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
        finally:
            session.close()
    
    def add_group(self, chat_id: int, chat_title: str = None, chat_type: str = None):
        """Add a new group to the database"""
        session = self.Session()
        try:
            # Check if group already exists
            existing_group = session.query(Group).filter_by(chat_id=chat_id).first()
            if existing_group:
                # Update group info
                existing_group.chat_title = chat_title
                existing_group.chat_type = chat_type
                existing_group.is_active = True
            else:
                # Create new group
                new_group = Group(
                    chat_id=chat_id,
                    chat_title=chat_title,
                    chat_type=chat_type
                )
                session.add(new_group)
                
                # Also create initial competition for this group
                new_competition = Competition(chat_id=chat_id)
                session.add(new_competition)
                
                # Initialize rollover count
                new_rollover = Rollover(chat_id=chat_id, count=0)
                session.add(new_rollover)
            
            session.commit()
            logger.info(f"Group {chat_id} added/updated successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding group {chat_id}: {e}")
        finally:
            session.close()
    
    def add_pick(self, user_id: int, round_number: int, team_name: str, team_id: int, result: str, chat_id: int):
        """Add a pick for a user"""
        session = self.Session()
        try:
            # Get current competition ID for this group
            competition = session.query(Competition).filter_by(chat_id=chat_id, is_active=True).first()
            competition_id = competition.id if competition else 1
            
            new_pick = Pick(
                user_id=user_id,
                round_number=round_number,
                team_name=team_name,
                team_id=team_id,
                result=result,
                chat_id=chat_id,
                competition_id=competition_id
            )
            session.add(new_pick)
            session.commit()
            logger.info(f"Pick added for user {user_id}: {team_name}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding pick for user {user_id}: {e}")
        finally:
            session.close()
    
    def get_user_pick_for_round(self, user_id: int, round_number: int):
        """Get user's pick for a specific round"""
        session = self.Session()
        try:
            pick = session.query(Pick).filter_by(
                user_id=user_id, 
                round_number=round_number
            ).first()
            
            if pick:
                return (pick.team_name, pick.team_id, pick.result)
            return None
        except Exception as e:
            logger.error(f"Error getting pick for user {user_id}, round {round_number}: {e}")
            return None
        finally:
            session.close()
    
    def get_current_survivors(self, chat_id: int):
        """Get all active users in a specific group"""
        session = self.Session()
        try:
            # Get current competition for this group
            competition = session.query(Competition).filter_by(chat_id=chat_id, is_active=True).first()
            if not competition:
                # If no competition exists, create one
                new_competition = Competition(chat_id=chat_id)
                session.add(new_competition)
                session.commit()
            
            # Get all active group members for this specific group
            active_members = session.query(GroupMember, User).join(
                User, GroupMember.user_id == User.user_id
            ).filter(
                GroupMember.chat_id == chat_id,
                GroupMember.is_active == True,
                User.is_active == True
            ).all()
            
            survivors = [(member.user_id, user.username) for member, user in active_members]
            
            return survivors
        except Exception as e:
            logger.error(f"Error getting survivors for group {chat_id}: {e}")
            return []
        finally:
            session.close()
    
    def has_used_team(self, user_id: int, team_id: int, chat_id: int):
        """Check if user has already used a team in current competition"""
        session = self.Session()
        try:
            # Get current competition for this group
            competition = session.query(Competition).filter_by(chat_id=chat_id, is_active=True).first()
            if not competition:
                return False
            
            pick = session.query(Pick).filter_by(
                user_id=user_id,
                team_id=team_id,
                chat_id=chat_id,
                competition_id=competition.id
            ).first()
            
            return pick is not None
        except Exception as e:
            logger.error(f"Error checking if user {user_id} used team {team_id}: {e}")
            return False
        finally:
            session.close()
    
    def eliminate_user(self, user_id: int, chat_id: int = None):
        """Mark user as eliminated (inactive) in a specific group or globally"""
        session = self.Session()
        try:
            if chat_id:
                # Eliminate user from specific group only
                member = session.query(GroupMember).filter_by(
                    user_id=user_id, 
                    chat_id=chat_id
                ).first()
                if member:
                    member.is_active = False
                    session.commit()
                    logger.info(f"User {user_id} eliminated from group {chat_id}")
            else:
                # Global elimination (eliminate from all groups)
                user = session.query(User).filter_by(user_id=user_id).first()
                if user:
                    user.is_active = False
                    # Also eliminate from all groups
                    members = session.query(GroupMember).filter_by(user_id=user_id).all()
                    for member in members:
                        member.is_active = False
                    session.commit()
                    logger.info(f"User {user_id} eliminated globally")
        except Exception as e:
            session.rollback()
            logger.error(f"Error eliminating user {user_id}: {e}")
        finally:
            session.close()
    
    def add_winner(self, user_id: int, chat_id: int):
        """Add a winner to the winners table"""
        session = self.Session()
        try:
            # Get current competition for this group
            competition = session.query(Competition).filter_by(chat_id=chat_id, is_active=True).first()
            competition_id = competition.id if competition else 1
            
            new_winner = Winner(
                user_id=user_id,
                chat_id=chat_id,
                competition_id=competition_id
            )
            session.add(new_winner)
            session.commit()
            logger.info(f"Winner added: user {user_id} in group {chat_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding winner {user_id}: {e}")
        finally:
            session.close()
    
    def reset_competition(self, chat_id: int):
        """Reset competition for a specific group"""
        session = self.Session()
        try:
            # Mark current competition as inactive
            current_competition = session.query(Competition).filter_by(chat_id=chat_id, is_active=True).first()
            if current_competition:
                current_competition.is_active = False
            
            # Create new competition
            new_competition = Competition(chat_id=chat_id)
            session.add(new_competition)
            session.commit()
            
            # Reactivate all group members for this specific group
            group_members = session.query(GroupMember).filter_by(chat_id=chat_id).all()
            for member in group_members:
                member.is_active = True
            
            # Also reactivate the users globally (in case they were globally eliminated)
            user_ids = [member.user_id for member in group_members]
            users = session.query(User).filter(User.user_id.in_(user_ids)).all()
            for user in users:
                user.is_active = True
            
            session.commit()
            
            logger.info(f"Competition reset for group {chat_id}")
            return new_competition.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error resetting competition for group {chat_id}: {e}")
            return None
        finally:
            session.close()
    
    def get_display_name(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Get display name for user"""
        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif first_name:
            return first_name
        elif username:
            return f"@{username}"
        else:
            return f"User{user_id}"
    
    def get_all_groups(self):
        """Get all active groups"""
        session = self.Session()
        try:
            groups = session.query(Group).filter_by(is_active=True).all()
            return [(group.chat_id, group.chat_title, group.chat_type) for group in groups]
        except Exception as e:
            logger.error(f"Error getting all groups: {e}")
            return []
        finally:
            session.close()
    
    def get_users_with_picks_for_round(self, round_number: int, chat_id: int):
        """Get all users who made picks for a specific round in a group"""
        session = self.Session()
        try:
            # Get current competition for this group
            competition = session.query(Competition).filter_by(chat_id=chat_id, is_active=True).first()
            if not competition:
                return []
            
            picks = session.query(Pick, User).join(User, Pick.user_id == User.user_id).filter(
                Pick.round_number == round_number,
                Pick.chat_id == chat_id,
                Pick.competition_id == competition.id
            ).all()
            
            return [(pick.user_id, user.username, user.first_name, user.last_name) 
                   for pick, user in picks]
        except Exception as e:
            logger.error(f"Error getting users with picks for round {round_number}: {e}")
            return []
        finally:
            session.close()
    
    def reset_rollover(self, chat_id: int):
        """Reset rollover count for a group"""
        session = self.Session()
        try:
            rollover = session.query(Rollover).filter_by(chat_id=chat_id).first()
            if rollover:
                rollover.count = 0
                rollover.updated_at = datetime.utcnow()
            else:
                rollover = Rollover(chat_id=chat_id, count=0)
                session.add(rollover)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error resetting rollover for group {chat_id}: {e}")
        finally:
            session.close()
