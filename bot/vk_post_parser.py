import re
from html import escape

def parse_vk_post_text(post_text):
    # Regular expression to match VK embeds (both "id" and "club")
    embed_pattern = r'\[(id|club)(\d+)\|([^\]]+)\]'

    def replace_embed(match):
        embed_type = match.group(1)
        entity_id = match.group(2)
        display_name = escape(match.group(3))
        
        if embed_type == 'id':
            vk_link = f'<a href="https://vk.com/id{entity_id}">{display_name}</a>'
        elif embed_type == 'club':
            vk_link = f'<a href="https://vk.com/club{entity_id}">{display_name}</a>'
        else:
            vk_link = match.group(0)  # Return the original text if neither "id" nor "club"
        
        return vk_link

    # Replace VK embeds with Telegram-compatible HTML hyperlinks
    parsed_text = re.sub(embed_pattern, replace_embed, post_text)

    return parsed_text

# Example usage:
vk_post_text = "Check out [id224339543|Романа Дрибаса]'s profile and [club35555742|Кейс-Клуб МФТИ]."
parsed_text = parse_vk_post_text(vk_post_text)
print(parsed_text)