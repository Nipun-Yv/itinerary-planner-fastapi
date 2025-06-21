def format_activity(activity_list):
    formatted_activity_string=""
    for i,activity in enumerate(activity_list):
        formatted_activity_string+=f"{i+1}. {activity['name']} ({activity['description']}, duration:{activity['duration']} minutes, latitude:{activity['latitude']}, longitude:{activity['longitude']} ,activity_id:{activity['id']})\n"
    return formatted_activity_string
