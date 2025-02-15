#-----------------------------------------------------------------------
# challenges_database.py
#-----------------------------------------------------------------------

import psycopg2
import random
import database
import versus_database

#-----------------------------------------------------------------------

DATABASE_URL = 'postgres://tigerspot_user:9WtP1U9PRdh1VLlP4VdwnT0BFSdbrPWk@dpg-cnrjs7q1hbls73e04390-a.ohio-postgres.render.com/tigerspot'

#-----------------------------------------------------------------------

# Creates challenge table
def create_challenges_table():
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute('''CREATE TABLE IF NOT EXISTS challenges(
                id SERIAL PRIMARY KEY,
                challenger_id VARCHAR(255),
                challengee_id VARCHAR(255),
                status VARCHAR(50));''')
                conn.commit()
    
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error clearing challenges table: {error}")
        return "database error"
#-----------------------------------------------------------------------
# Reset challenges tables
def clear_challenges_table():
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Deletes all records from the challenges table
                cur.execute("DELETE FROM challenges;")
                conn.commit()  # Commit the transaction to make changes permanent
                print("Challenges table cleared.")
                cur.execute("DELETE FROM matches;")
                conn.commit()  # Commit the transaction to make changes permanent
                print("Matches table cleared.")
                cur.execute("ALTER SEQUENCE challenges_id_seq RESTART WITH 1;")
                conn.commit()  # Commit the change to make it permanent
                print("Challenges id sequence reset.")
                cur.execute("ALTER SEQUENCE matches_id_seq RESTART WITH 1;")
                conn.commit()  # Commit the change to make it permanent
                print("Matches id sequence reset.")
                return "success"
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error clearing challenges table: {error}")
        return "database error"
 
#-----------------------------------------------------------------------
# Reset challenges pertaining to a certain user
def clear_user_challenges(user_id):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:

                # Query to find challenges related to the user_id
                cur.execute("""
                    SELECT id FROM challenges 
                    WHERE challenger_id = %s OR challengee_id = %s;
                """, (user_id, user_id))

                challenge_ids = [row[0] for row in cur.fetchall()]
                
                if challenge_ids:
                    # Delete matching entries from the matches table
                    cur.execute("""
                        DELETE FROM matches 
                        WHERE challenge_id IN %s;
                    """, (tuple(challenge_ids),))
                    
                    # Delete entries from the challenges table
                    cur.execute("""
                        DELETE FROM challenges 
                        WHERE id IN %s;
                    """, (tuple(challenge_ids),))

                conn.commit()  # Commit the transaction to make changes permanent
                return "success"
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error clearing entries for user_id {user_id}: {error}")
        return "database error"

#-----------------------------------------------------------------------

# Create a new challenge row between new users
def create_challenge(challenger_id, challengee_id):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:

                # Check for existing challenge between the two users
                cur.execute("""
                    SELECT id FROM challenges 
                    WHERE 
                        ((challenger_id = %s AND challengee_id = %s) OR 
                        (challenger_id = %s AND challengee_id = %s)) 
                        AND status IN ('pending', 'accepted')
                    """, (challenger_id, challengee_id, challengee_id, challenger_id))

                existing_challenge = cur.fetchone()

                if existing_challenge:
                    # An existing challenge was found
                    return {'error': 'Challenge already exists', 'challenge_id': existing_challenge[0]}

                # No existing challenge found, proceed to create a new one
                cur.execute("""
                    INSERT INTO challenges (challenger_id, challengee_id, status) 
                    VALUES (%s, %s, 'pending') RETURNING id;
                    """, (challenger_id, challengee_id))
                
                challenge_id = cur.fetchone()[0]
                conn.commit()
                return {'success': 'Challenge created successfully', 'challenge_id': challenge_id}
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return "database error"
            
#-----------------------------------------------------------------------

# Accept a challenge
def accept_challenge(challenge_id):
    status = "database error"  # Default status in case of error
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Update the status of the challenge to 'accepted' and create a random versusList
                cur.execute("""
                    UPDATE challenges 
                    SET status = 'accepted', 
                        versusList = %s
                    WHERE id = %s;
                """, (create_random_versus(), challenge_id))
                conn.commit()
                status = "accepted"  # Update status on success
        return status
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return "database error"

#-----------------------------------------------------------------------

# Decline a challenge
def decline_challenge(challenge_id):
    status = "database error"  # Default status in case of error
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Update the status of the challenge to 'declined'
                cur.execute("UPDATE challenges SET status = 'declined' WHERE id = %s;", (challenge_id,))
                conn.commit()
                status = "declined"
        return status
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return "database error"

#-----------------------------------------------------------------------

# Retrieve all challenges that a user is involved in
def get_user_challenges(user_id):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Query for both challenges initiated by the user and challenges where the user is the challengee,
                # including whether each side has finished the challenge.
                cur.execute("""
                    SELECT challenges.id, challenger_id, challengee_id, status, challenger_finished, challengee_finished
                    FROM challenges
                    WHERE (challenges.challenger_id = %s OR challenges.challengee_id = %s);
                    """, (user_id, user_id))
                challenges = cur.fetchall()
                
                # Initialize dictionaries to hold the two types of challenges
                user_challenges = {'initiated': [], 'received': []}
                
                # Iterate through the results and categorize each challenge
                for challenge in challenges:
                    # Add challenger_finished and challengee_finished to the dictionary
                    if versus_database.get_winner(challenge[0]) is not None:
                        challenge_dict = {
                            "id": challenge[0], 
                            "challenger_id": challenge[1], 
                            "challengee_id": challenge[2], 
                            "status": challenge[3],
                            "challenger_finished": challenge[4],
                            "challengee_finished": challenge[5],
                            "winner_id": versus_database.get_winner(challenge[0])
                        }
                    else:
                        challenge_dict = {
                            "id": challenge[0], 
                            "challenger_id": challenge[1], 
                            "challengee_id": challenge[2], 
                            "status": challenge[3],
                            "challenger_finished": challenge[4],
                            "challengee_finished": challenge[5],
                            "winner_id": None
                        }
                    if challenge[1] == user_id:  # User is the challenger
                        user_challenges['initiated'].append(challenge_dict)
                    else:  # User is the challengee
                        user_challenges['received'].append(challenge_dict)
        return user_challenges
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error getting user challenges: {error}")
        return "database error"

#-----------------------------------------------------------------------

# Update if a given user has finished a given challenge
def update_finish_status(challenge_id, user_id):
    try:
       with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # First, determine if the user is the challenger or the challengee for this challenge
                cur.execute('''
                    SELECT challenger_id, challengee_id 
                    FROM challenges 
                    WHERE id = %s;
                ''', (challenge_id,))
                
                result = cur.fetchone()
                if result is None:
                    # Challenge not found
                    return
                
                challenger_id, challengee_id = result
                
                # Depending on whether the user is the challenger or the challengee,
                # update the corresponding finished column in the matches table
                if user_id == challenger_id:
                    cur.execute('''
                        UPDATE challenges 
                        SET challenger_finished = TRUE 
                        WHERE id = %s;
                    ''', (challenge_id,))
                elif user_id == challengee_id:
                    cur.execute('''
                        UPDATE challenges
                        SET challengee_finished = TRUE 
                        WHERE id = %s;
                    ''', (challenge_id,))
                else:
                    # User is not part of this challenge
                    return
                
                conn.commit()
                return "success"
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        return "database error"

#-----------------------------------------------------------------------

# Check if both users have finished a given challenge
def check_finish_status(challenge_id):
    status = {"status": "unfinished"}  # Default status
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                
                # Query to check the finish status for both challenger and challengee
                cur.execute('''
                    SELECT challenger_finished, challengee_finished
                    FROM challenges
                    WHERE id = %s;
                ''', (challenge_id,))
                
                result = cur.fetchone()
                if result:
                    challenger_finished, challengee_finished = result
                    if challenger_finished and challengee_finished:
                        status = {"status": "finished"}
                else:
                    print("No match found with the given challenge_id.")
        return status
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error checking finish status: {error}")
        return "database error"

#-----------------------------------------------------------------------

# Get the participants of a given challenge
def get_challenge_participants(challenge_id):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                
                # SQL query to select challenger_id and challengee_id from the challenges table
                cur.execute('''
                    SELECT challenger_id, challengee_id
                    FROM challenges
                    WHERE id = %s;
                ''', (challenge_id,))
                
                result = cur.fetchone()
                if result:
                    # Unpack the result
                    challenger_id, challengee_id = result
                    participants = {
                        "challenger_id": challenger_id,
                        "challengee_id": challengee_id
                    }
                    return participants
                else:
                    # No challenge found with the given ID 
                    return None    
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Database error: {error}")
        return "database error"

#-----------------------------------------------------------------------

# Get the results of a given challenge and return a dictionary of related result information
def get_challenge_results(challenge_id):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                
                # Query to get challenger and challengee points for the given challenge ID
                cur.execute('''
                    SELECT challenger_id, challengee_id, challenger_points, challengee_points, challenger_pic_points, challengee_pic_points
                    FROM challenges
                    WHERE id = %s;
                ''', (challenge_id,))
                
                result = cur.fetchone()
                if result is None:
                    print("Challenge not found.")
                    return

                challenger_id, challengee_id, challenger_points, challengee_points, challenger_pic_points, challengee_pic_points = result
                
                # Determine the winner or if it's a tie
                if challenger_points > challengee_points:
                    winner = challenger_id
                elif challengee_points > challenger_points:
                    winner = challengee_id
                else:
                    winner = "Tie"
                
                # Return a dictionary with the results
                return {
                    "winner": winner,
                    "challenger_id": challenger_id,
                    "challengee_id": challengee_id,
                    "challenger_points": challenger_points,
                    "challengee_points": challengee_points,
                    "challenge_id": challenge_id,
                    "challenger_pic_points": challenger_pic_points,
                    "challengee_pic_points": challengee_pic_points,
                }        
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        return "database error"
    
#-----------------------------------------------------------------------

# pseudo randomly create a list of 5 picture IDs for a challenge
def create_random_versus():
    random.seed()
    row_count = database.get_table_size('pictures')
    
    # Generate 5 unique pseudo-random integers from 1 to row_count
    random_indices = random.sample(range(1, row_count + 1), 5)
    
    return random_indices

#-----------------------------------------------------------------------

# Return the versusList for a given challenge ID
def get_random_versus(challenge_id):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                
                # Query to get the versusList for the given challenge ID
                cur.execute('''
                    SELECT versusList
                    FROM challenges
                    WHERE id = %s;
                ''', (challenge_id,))
                
                result = cur.fetchone()
                if result is None:
                    # Challenge not found
                    return
                
                versusList = result[0]
        return versusList
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        return "database error"

#-----------------------------------------------------------------------

# Update if a player has started a given challenge or not
def update_playbutton_status(challenge_id, user_id):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                
                # First, determine if the user is the challenger or the challengee for this challenge
                cur.execute('''
                    SELECT challenger_id, challengee_id
                    FROM challenges
                    WHERE id = %s;
                ''', (challenge_id,))
                
                result = cur.fetchone()
                if result is None:
                    # Challenge not found
                    return
                
                challenger_id, challengee_id = result
                
                # Depending on whether the user is the challenger or the challengee,
                # update the corresponding finished column in the matches table
                if user_id == challenger_id:
                    cur.execute('''
                        UPDATE challenges
                        SET playger_button_status = TRUE
                        WHERE id = %s;
                    ''', (challenge_id,))
                elif user_id == challengee_id:
                    cur.execute('''
                        UPDATE challenges
                        SET playgee_button_status = TRUE
                        WHERE id = %s;
                    ''', (challenge_id,))
                else:
                    # User is not part of this challenge
                    return
                
                conn.commit()
                return "success"
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        return "database error"
    
#-----------------------------------------------------------------------

# Get the play button status for a given user in a given challenge
def get_playbutton_status(challenge_id, user_id):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                
                # First, determine if the user is the challenger or the challengee for this challenge
                cur.execute('''
                    SELECT challenger_id, challengee_id
                    FROM challenges
                    WHERE id = %s;
                ''', (challenge_id,))
                
                result = cur.fetchone()
                if result is None:
                    print("Challenge not found.")
                    return
                
                challenger_id, challengee_id = result
                
                # Depending on whether the user is the challenger or the challengee,
                # update the corresponding finished column in the matches table
                if user_id == challenger_id:
                    cur.execute('''
                        SELECT playger_button_status
                        FROM challenges
                        WHERE id = %s;
                    ''', (challenge_id,))
                elif user_id == challengee_id:
                    cur.execute('''
                        SELECT playgee_button_status
                        FROM challenges
                        WHERE id = %s;
                    ''', (challenge_id,))
                else:
                    # User is not part of this challenge
                    return
                
                result = cur.fetchone()
                if result is not None:
                    return result[0]
                else:
                    # No results found
                    return None
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        return "database error"
    
#-----------------------------------------------------------------------

def main():

    # Testing
    print('Testing')
    #print(create_challenge('123', '456'))
    #print(create_challenge('abc', 'def'))
    #print(accept_challenge('1'))
    #print(decline_challenge('2'))
    #print(get_user_challenges('abc'))
    #print(update_finish_status('1', '123'))
    #print(check_finish_status('1'))
    #print(get_challenge_participants('1'))
    #print(get_challenge_results('1'))
    #print(create_random_versus())
    #print(get_random_versus('1'))
    #print(update_playbutton_status('1', '123'))
    #print(get_playbutton_status('1', '123'))
    #print(clear_user_challenges('123'))
    #print(clear_user_challenges('abc'))
    #print(clear_challenges_table())

#-----------------------------------------------------------------------
    
if __name__=="__main__":
    main()