# To run this, you'll need to install Flask and Flask-CORS:
# pip install Flask Flask-CORS

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from collections import deque

# --- Basic Setup ---
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- Directories for Levels ---
LEVELS_DIR = 'levels'
DEFAULT_LEVELS_DIR = 'default_levels'

# --- AI Pathfinding Logic (BFS Algorithm) ---

def find_path(grid, start, end):
    """
    Finds the shortest path from start to end using Breadth-First Search (BFS).
    'grid' is a 2D list where 0 is open space and 1 is a wall.
    'start' and 'end' are (row, col) tuples.
    """
    queue = deque([[start]])
    seen = {start}
    
    if start == end:
        return [start]

    while queue:
        path = queue.popleft()
        r, c = path[-1]

        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]: # 4-directional movement
            nr, nc = r + dr, c + dc

            if (0 <= nr < len(grid) and 0 <= nc < len(grid[0]) and
                    grid[nr][nc] == 0 and (nr, nc) not in seen):
                
                new_path = list(path)
                new_path.append((nr, nc))
                seen.add((nr, nc))

                if (nr, nc) == end:
                    return new_path
                
                queue.append(new_path)
    return None # No path found

# --- API Routes ---

@app.route('/')
def serve_index():
    """Serves the main HTML file."""
    return send_from_directory('.', 'index.html')

@app.route('/api/ai-move', methods=['POST'])
def get_ai_move():
    """
    Calculates the next move for an AI enemy.
    Expects JSON with game state: { "grid_size": 32, "width": 640, "height": 480, "objects": [...] }
    """
    try:
        state = request.get_json()
        width = state['width']
        height = state['height']
        grid_size = state['grid_size']
        objects = state['objects']
        
        cols = width // grid_size
        rows = height // grid_size

        # Create a grid representation for pathfinding
        grid = [[0] * cols for _ in range(rows)]
        player_pos, ai_pos = None, None

        for obj in objects:
            r, c = obj['y'] // grid_size, obj['x'] // grid_size
            if obj['type'] in ['wall', 'enemy']: # Treat static enemies as walls
                grid[r][c] = 1
            elif obj['type'] == 'player':
                player_pos = (r, c)
            elif obj['type'] == 'ai_enemy':
                ai_pos = (r, c)
        
        if not player_pos or not ai_pos:
            return jsonify({"status": "error", "message": "Player or AI not found"}), 400

        # Find path from AI to Player
        path = find_path(grid, ai_pos, player_pos)

        if path and len(path) > 1:
            # The next step is the second element in the path
            next_r, next_c = path[1]
            return jsonify({
                "status": "success",
                "next_x": next_c * grid_size,
                "next_y": next_r * grid_size
            })
        else:
            # No path found, or already at player. AI doesn't move.
            return jsonify({
                "status": "no_move",
                "next_x": ai_pos[1] * grid_size,
                "next_y": ai_pos[0] * grid_size
            })

    except Exception as e:
        print(f"Error in AI move calculation: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route('/api/save', methods=['POST'])
def save_level():
    """Saves a user-created level design to a JSON file."""
    # (This function is unchanged)
    try:
        level_data = request.get_json()
        level_name = level_data.get('name')
        game_objects = level_data.get('data')

        if not level_name or not isinstance(game_objects, list):
            return jsonify({"status": "error", "message": "Invalid data format"}), 400

        if not os.path.exists(LEVELS_DIR):
            os.makedirs(LEVELS_DIR)

        safe_filename = "".join(c for c in level_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filepath = os.path.join(LEVELS_DIR, f"{safe_filename}.json")

        with open(filepath, 'w') as f:
            json.dump(game_objects, f, indent=2)

        return jsonify({"status": "success", "message": f"Level '{safe_filename}' saved."})
    except Exception as e:
        print(f"Error saving level: {e}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500


@app.route('/api/levels', methods=['GET'])
def get_levels():
    """Lists all available saved levels, including user-made and default."""
    levels = []
    # Get user-saved levels
    if os.path.exists(LEVELS_DIR):
        user_levels = [f.replace('.json', '') for f in os.listdir(LEVELS_DIR) if f.endswith('.json')]
        levels.extend([{"name": name, "type": "user"} for name in user_levels])

    # Get default levels
    if os.path.exists(DEFAULT_LEVELS_DIR):
        default_levels = [f.replace('.json', '') for f in os.listdir(DEFAULT_LEVELS_DIR) if f.endswith('.json')]
        levels.extend([{"name": name, "type": "default"} for name in default_levels])
        
    return jsonify(levels)


@app.route('/api/load/<level_type>/<level_name>', methods=['GET'])
def load_level(level_type, level_name):
    """Loads a specific level's data from its JSON file."""
    # (This function is updated to handle default levels)
    base_dir = DEFAULT_LEVELS_DIR if level_type == 'default' else LEVELS_DIR
    
    try:
        safe_filename = "".join(c for c in level_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filepath = os.path.join(base_dir, f"{safe_filename}.json")

        if not os.path.exists(filepath):
            return jsonify({"status": "error", "message": "Level not found."}), 404

        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        print(f"Error loading level: {e}")
        return jsonify({"status": "error", "message": "Could not load level."}), 500

def setup_default_levels():
    """Creates the default levels directory and files if they don't exist."""
    if not os.path.exists(DEFAULT_LEVELS_DIR):
        os.makedirs(DEFAULT_LEVELS_DIR)

    # --- Maze Runner Game ---
    maze_runner = [
      {"type": "player", "x": 32, "y": 32},
      {"type": "goal", "x": 576, "y": 416},
      {"type": "wall", "x": 0, "y": 0}, {"type": "wall", "x": 32, "y": 0}, {"type": "wall", "x": 64, "y": 0}, {"type": "wall", "x": 96, "y": 0}, {"type": "wall", "x": 128, "y": 0}, {"type": "wall", "x": 160, "y": 0}, {"type": "wall", "x": 192, "y": 0}, {"type": "wall", "x": 224, "y": 0}, {"type": "wall", "x": 256, "y": 0}, {"type": "wall", "x": 288, "y": 0}, {"type": "wall", "x": 320, "y": 0}, {"type": "wall", "x": 352, "y": 0}, {"type": "wall", "x": 384, "y": 0}, {"type": "wall", "x": 416, "y": 0}, {"type": "wall", "x": 448, "y": 0}, {"type": "wall", "x": 480, "y": 0}, {"type": "wall", "x": 512, "y": 0}, {"type": "wall", "x": 544, "y": 0}, {"type": "wall", "x": 576, "y": 0}, {"type": "wall", "x": 608, "y": 0},
      {"type": "wall", "x": 0, "y": 32}, {"type": "wall", "x": 0, "y": 64}, {"type": "wall", "x": 0, "y": 96}, {"type": "wall", "x": 0, "y": 128}, {"type": "wall", "x": 0, "y": 160}, {"type": "wall", "x": 0, "y": 192}, {"type": "wall", "x": 0, "y": 224}, {"type": "wall", "x": 0, "y": 256}, {"type": "wall", "x": 0, "y": 288}, {"type": "wall", "x": 0, "y": 320}, {"type": "wall", "x": 0, "y": 352}, {"type": "wall", "x": 0, "y": 384}, {"type": "wall", "x": 0, "y": 416}, {"type": "wall", "x": 0, "y": 448},
      {"type": "wall", "x": 608, "y": 32}, {"type": "wall", "x": 608, "y": 64}, {"type": "wall", "x": 608, "y": 96}, {"type": "wall", "x": 608, "y": 128}, {"type": "wall", "x": 608, "y": 160}, {"type": "wall", "x": 608, "y": 192}, {"type": "wall", "x": 608, "y": 224}, {"type": "wall", "x": 608, "y": 256}, {"type": "wall", "x": 608, "y": 288}, {"type": "wall", "x": 608, "y": 320}, {"type": "wall", "x": 608, "y": 352}, {"type": "wall", "x": 608, "y": 384}, {"type": "wall", "x": 608, "y": 416}, {"type": "wall", "x": 608, "y": 448},
      {"type": "wall", "x": 32, "y": 448}, {"type": "wall", "x": 64, "y": 448}, {"type": "wall", "x": 96, "y": 448}, {"type": "wall", "x": 128, "y": 448}, {"type": "wall", "x": 160, "y": 448}, {"type": "wall", "x": 192, "y": 448}, {"type": "wall", "x": 224, "y": 448}, {"type": "wall", "x": 256, "y": 448}, {"type": "wall", "x": 288, "y": 448}, {"type": "wall", "x": 320, "y": 448}, {"type": "wall", "x": 352, "y": 448}, {"type": "wall", "x": 384, "y": 448}, {"type": "wall", "x": 416, "y": 448}, {"type": "wall", "x": 448, "y": 448}, {"type": "wall", "x": 480, "y": 448}, {"type": "wall", "x": 512, "y": 448}, {"type": "wall", "x": 544, "y": 448}, {"type": "wall", "x": 576, "y": 448},
      {"type": "wall", "x": 96, "y": 64}, {"type": "wall", "x": 96, "y": 96}, {"type": "wall", "x": 96, "y": 128}, {"type": "wall", "x": 96, "y": 160}, {"type": "wall", "x": 96, "y": 192},
      {"type": "wall", "x": 192, "y": 320}, {"type": "wall", "x": 192, "y": 352}, {"type": "wall", "x": 192, "y": 384}, {"type": "wall", "x": 192, "y": 416},
      {"type": "wall", "x": 288, "y": 64}, {"type": "wall", "x": 288, "y": 96}, {"type": "wall", "x": 288, "y": 128}, {"type": "wall", "x": 288, "y": 160}, {"type": "wall", "x": 288, "y": 192},
      {"type": "wall", "x": 384, "y": 320}, {"type": "wall", "x": 384, "y": 352}, {"type": "wall", "x": 384, "y": 384}, {"type": "wall", "x": 384, "y": 416},
      {"type": "wall", "x": 480, "y": 64}, {"type": "wall", "x": 480, "y": 96}, {"type": "wall", "x": 480, "y": 128}, {"type": "wall", "x": 480, "y": 160}, {"type": "wall", "x": 480, "y": 192},
      {"type": "ai_enemy", "x": 544, "y": 64}, {"type": "ai_enemy", "x": 64, "y": 384}
    ]
    with open(os.path.join(DEFAULT_LEVELS_DIR, 'maze_runner.json'), 'w') as f:
        json.dump(maze_runner, f)

    # --- Dodge Em Game ---
    dodge_em = [
        {"type": "player", "x": 320, "y": 416},
        {"type": "goal", "x": 320, "y": 32},
        {"type": "ai_enemy", "x": 32, "y": 128},
        {"type": "ai_enemy", "x": 64, "y": 288},
        {"type": "ai_enemy", "x": 576, "y": 128},
        {"type": "ai_enemy", "x": 544, "y": 288},
        {"type": "wall", "x": 160, "y": 224}, {"type": "wall", "x": 192, "y": 224}, {"type": "wall", "x": 224, "y": 224},
        {"type": "wall", "x": 448, "y": 224}, {"type": "wall", "x": 416, "y": 224}, {"type": "wall", "x": 384, "y": 224}
    ]
    with open(os.path.join(DEFAULT_LEVELS_DIR, 'dodge_em.json'), 'w') as f:
        json.dump(dodge_em, f)


# --- Main Execution ---
if __name__ == '__main__':
    setup_default_levels() # Create the default games on startup
    app.run(host='0.0.0.0', port=5000, debug=True)
