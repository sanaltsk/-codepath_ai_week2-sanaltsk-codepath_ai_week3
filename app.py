import json

from dotenv import load_dotenv
import chainlit as cl
from movie_functions import get_now_playing_movies, get_showtimes,get_reviews
load_dotenv()

# Note: If switching to LangSmith, uncomment the following, and replace @observe with @traceable
# from langsmith.wrappers import wrap_openai
# from langsmith import traceable
# client = wrap_openai(openai.AsyncClient())

from langfuse.decorators import observe
from langfuse.openai import AsyncOpenAI
 
client = AsyncOpenAI()

gen_kwargs = {
    "model": "gpt-4o",
    "temperature": 0.2,
    "max_tokens": 500
}

SYSTEM_PROMPT = """
You are a helpful assistant.
When asked about movies showtimes, you will create a message with the movie title and location formatted as 
{ "function": "get_showtimes", "title": "movieTitle", "location": "city, state"}
When asked about current movies playing, you will create a message formatted as 
{ "function": "get_now_playing_movies"}
When asked about the reviews for a movie, you will create a message formatted as
{ "function": "get_reviews", "movie_id": "movieId" }
"""

@observe
@cl.on_chat_start
def on_chat_start():    
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)

@observe
async def generate_response(client, message_history, gen_kwargs):
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(messages=message_history, stream=True, **gen_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)
    
    await response_message.update()

    return response_message

@cl.on_message
@observe
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    
    response_message = await generate_response(client, message_history, gen_kwargs)

    try:
        function_call = json.loads(response_message.content)
        if "function" in function_call:
            if function_call["function"]=="get_now_playing_movies":
                current_movies = get_now_playing_movies()
                message_history.append({"role": "system", "content":  f"Result of get_now_playing_movies:{current_movies}"})
                response_message = await generate_response(client, message_history, gen_kwargs)
            elif function_call["function"]=="get_showtimes":
                show_times = get_showtimes(function_call["title"], function_call["location"])
                message_history.append({"role": "system", "content":  f"Result of get_showtimes:{show_times}"})
                response_message = await generate_response(client, message_history, gen_kwargs)
            elif function_call["function"] == "get_reviews":
                review = get_reviews(function_call["movie_id"])
                message_history.append({"role": "system", "content": f"Result of get_reviews:{review}"})
                response_message = await generate_response(client, message_history, gen_kwargs)
    except:
        print("error")
    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)

# if function_call["function"] == "get_now_playing_movies":
#     api_response = get_now_playing_movies()
# elif function_call["function"] == "get_showtimes":
#     api_response = get_showtimes(function_call["title"], function_call["location"])
# elif function_call["function"] == "get_reviews":
#     api_response = get_reviews(function_call["movie_id"])
# message_history.append({"role": "system", "content": f"Result of get_reviews:{api_response}"})