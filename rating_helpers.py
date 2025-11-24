"""
Rating Helper Functions for AUBus
Provides functions to interact with the rating system
"""

def get_user_rating(server_network, user_id, role="driver"):
    """
    Retrieve the average rating for a user from the server
    
    Args:
        server_network: The network manager instance
        user_id: ID of the user to get rating for
        role: "driver" or "passenger"
    
    Returns:
        float: Average rating (0.0 if no ratings)
        int: Number of ratings
    """
    try:
        command = f"RATING_GET|{user_id}|{role}"
        response = server_network.send_protocol_command(command)
        
        print(f"Rating response: {response}")
        
        if "SUCCESS" in response:
            # Response format: SUCCESS|Driver 123|Average=4.75|Count=20
            # OR: SUCCESS|Driver 123 has no ratings
            
            if "no ratings" in response.lower():
                return 0.0, 0
            
            parts = response.split("|")
            if len(parts) >= 3:
                # Parse average
                avg_part = parts[2]  # "Average=4.75"
                if "=" in avg_part:
                    avg_value = float(avg_part.split("=")[1])
                else:
                    return 0.0, 0
                
                # Parse count
                count_value = 0
                if len(parts) >= 4:
                    count_part = parts[3]  # "Count=20"
                    if "=" in count_part:
                        count_value = int(count_part.split("=")[1])
                
                return avg_value, count_value
        
        return 0.0, 0
        
    except Exception as e:
        print(f"Error getting rating: {e}")
        import traceback
        traceback.print_exc()
        return 0.0, 0


def submit_rating(server_network, request_id, rater_id, target_id, target_role, rating, comment=""):
    """
    Submit a rating to the server
    
    Args:
        server_network: The network manager instance
        request_id: ID of the ride request
        rater_id: ID of the user submitting the rating
        target_id: ID of the user being rated
        target_role: "driver" or "passenger"
        rating: Integer rating (1-5)
        comment: Optional comment
    
    Returns:
        bool: True if successful, False otherwise
        str: Response message
    """
    try:
        # Format: RATING_SUBMIT|request_id|rater_id|target_id|target_role|rating|comment
        command = f"RATING_SUBMIT|{request_id}|{rater_id}|{target_id}|{target_role}|{rating}|{comment}"
        response = server_network.send_protocol_command(command)
        
        print(f"Rating submission response: {response}")
        
        if "SUCCESS" in response:
            return True, response
        else:
            return False, response
            
    except Exception as e:
        error_msg = f"Error submitting rating: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return False, error_msg


def get_rating_history(server_network, user_id, role="driver", limit=10, offset=0):
    """
    Get rating history for a user
    
    Args:
        server_network: The network manager instance
        user_id: ID of the user
        role: "driver" or "passenger"
        limit: Number of ratings to retrieve
        offset: Offset for pagination
    
    Returns:
        list: List of rating dictionaries, or empty list
    """
    try:
        command = f"RATING_HISTORY_GET|{user_id}|{role}|{limit}|{offset}"
        response = server_network.send_protocol_command(command)
        
        print(f"Rating history response: {response}")
        
        if "SUCCESS" in response and "no rating history" not in response.lower():
            # Response format: SUCCESS|Driver 123|req1|Rater=5|4|Great!|2024-01-01;req2|Rater=6|5||2024-01-02
            parts = response.split("|")
            
            if len(parts) >= 3:
                # Skip SUCCESS and user info, parse the rest
                history_data = parts[2:]
                ratings = []
                
                # Parse semicolon-separated ratings
                history_string = "|".join(history_data)
                rating_entries = history_string.split(";")
                
                for entry in rating_entries:
                    try:
                        # Format: request_id|Rater=rater_id|rating|comment|timestamp
                        entry_parts = entry.split("|")
                        if len(entry_parts) >= 4:
                            rating_dict = {
                                'request_id': entry_parts[0],
                                'rater_id': entry_parts[1].split("=")[1] if "=" in entry_parts[1] else "Unknown",
                                'rating': int(entry_parts[2]),
                                'comment': entry_parts[3],
                                'timestamp': entry_parts[4] if len(entry_parts) > 4 else ""
                            }
                            ratings.append(rating_dict)
                    except Exception as parse_error:
                        print(f"Error parsing rating entry: {parse_error}")
                        continue
                
                return ratings
        
        return []
        
    except Exception as e:
        print(f"Error getting rating history: {e}")
        import traceback
        traceback.print_exc()
        return []


def format_rating_display(avg_rating, count):
    """
    Format rating for display in UI
    
    Args:
        avg_rating: Average rating value
        count: Number of ratings
    
    Returns:
        str: Formatted rating string
    """
    if count == 0:
        return "⭐ No ratings yet"
    
    # Show stars based on rating
    stars = "⭐" * int(round(avg_rating))
    return f"{stars} {avg_rating:.1f}/5 ({count} ratings)"


def get_rating_stars(rating):
    """
    Get star representation of a rating
    
    Args:
        rating: Numeric rating (0-5)
    
    Returns:
        str: Star string
    """
    if rating == 0:
        return "☆☆☆☆☆"
    
    full_stars = int(rating)
    half_star = 1 if (rating - full_stars) >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    
    return "★" * full_stars + ("½" if half_star else "") + "☆" * empty_stars


# Validation functions
def validate_rating_value(rating):
    """Validate rating is between 1-5"""
    try:
        rating_int = int(rating)
        return 1 <= rating_int <= 5
    except:
        return False


def validate_user_ids(rater_id, target_id):
    """Validate user IDs are valid"""
    try:
        return int(rater_id) > 0 and int(target_id) > 0 and rater_id != target_id
    except:
        return False
