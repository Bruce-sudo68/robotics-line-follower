import pygame
import math

pygame.init()

# --- Simulation Parameters ---
WIDTH, HEIGHT = 800, 600
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Line-Following Robot (Fresh Start)")
clock = pygame.time.Clock()
FPS = 60

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0) # Our line color
ROBOT_COLOR = (220, 20, 60) # Crimson
SENSOR_COLOR_ACTIVE = (0, 255, 0) # Green when on line
SENSOR_COLOR_PASSIVE = (255, 0, 0) # Red when off line
DEBUG_TEXT_COLOR = (0, 0, 255) # Blue for debug text

# --- Robot Properties ---
# Initial position: Center of the robot on the track's starting point
# The track is a 25px thick black line.
# Outer rect starts at (100, 100), so black line is between 100 and 125 for X and Y in the corner.
# Let's place the robot such that its central sensor is roughly in the middle of the line (100 + 25/2 = 112.5)
# If the sensor is sensor_forward_distance ahead of robot_pos, then robot_pos should be
# 112.5 - sensor_forward_distance.
robot_radius = 15 # A bit larger for visibility
sensor_forward_distance = 20 # Distance of sensors from robot's center (forward)
sensor_lateral_offset = 15 # Distance of left/right sensors from center sensor (sideways)

robot_pos = [100 + (25 / 2), 100 + (25 / 2)] # Start in the center of the top-left corner line
robot_angle = 0 # Robot starts facing right (along the top line segment)

BASE_ROBOT_SPEED = 2 # Initial speed, can be adjusted
TURN_RATE = 2 # Degrees per step when turning

# --- Line Following Control Constants (PID-like) ---
# These weights determine how strongly the robot turns based on which sensors are active.
# Negative weights for left turns, positive for right turns.
# Center sensor (0) means no immediate turn needed.
SENSOR_WEIGHTS = {
    'left_forward': -3.0,
    'left': -2.0,
    'center': 0.0,
    'right': 2.0,
    'right_forward': 3.0,
}

# --- Robot Modes and Lost Line Logic ---
ROBOT_MODE = "FOLLOW_LINE"
LOST_LINE_COUNTER = 0
MAX_LOST_TIME_FRAMES = 120 # How many frames (2 seconds at 60 FPS) before stopping search

# --- Fonts for Debugging ---
font = pygame.font.Font(None, 24)

# --- Functions ---

def draw_track():
    """Draws the black track on a white background."""
    track_thickness = 25
    outer_rect = pygame.Rect(100, 100, 600, 400) # Outer boundary of the track
    inner_rect = pygame.Rect(
        100 + track_thickness,
        100 + track_thickness,
        600 - (2 * track_thickness),
        400 - (2 * track_thickness)
    )
    pygame.draw.rect(WIN, BLACK, outer_rect) # Draw outer black rectangle
    pygame.draw.rect(WIN, WHITE, inner_rect) # Draw inner white rectangle, creating the track

def draw_robot(x, y, angle):
    """Draws the robot as a triangle."""
    # Front point
    point1 = (x + math.cos(math.radians(angle)) * robot_radius,
              y + math.sin(math.radians(angle)) * robot_radius)
    # Rear-left point
    point2 = (x + math.cos(math.radians(angle + 140)) * robot_radius,
              y + math.sin(math.radians(angle + 140)) * robot_radius)
    # Rear-right point
    point3 = (x + math.cos(math.radians(angle - 140)) * robot_radius,
              y + math.sin(math.radians(angle - 140)) * robot_radius)
    pygame.draw.polygon(WIN, ROBOT_COLOR, [point1, point2, point3])

def get_pixel_color(x, y):
    """Safely gets the color of a pixel at (x, y) on the screen."""
    # Ensure coordinates are within screen bounds
    if 0 <= int(x) < WIDTH and 0 <= int(y) < HEIGHT:
        return WIN.get_at((int(x), int(y)))[:3] # Return RGB tuple
    else:
        # If sensor is outside screen, assume it's off the line (e.g., white background)
        return WHITE

def is_on_line(color, line_color=BLACK, tolerance=80): # Increased tolerance
    """Checks if a given color is close enough to the line color."""
    # Calculate absolute difference for each color component
    r_diff = abs(color[0] - line_color[0])
    g_diff = abs(color[1] - line_color[1])
    b_diff = abs(color[2] - line_color[2])
    # If all differences are within tolerance, it's considered on the line
    return (r_diff < tolerance) and (g_diff < tolerance) and (b_diff < tolerance)

def calculate_sensor_positions(robot_x, robot_y, robot_angle):
    """Calculates the world coordinates for each sensor."""
    sensors = {}
    
    # Calculate center sensor position (forward from robot center)
    sensors['center'] = (robot_x + math.cos(math.radians(robot_angle)) * sensor_forward_distance,
                         robot_y + math.sin(math.radians(robot_angle)) * sensor_forward_distance)

    # Calculate left sensor position (forward and left from robot center)
    sensors['left'] = (sensors['center'][0] + math.cos(math.radians(robot_angle - 90)) * sensor_lateral_offset,
                       sensors['center'][1] + math.sin(math.radians(robot_angle - 90)) * sensor_lateral_offset)

    # Calculate right sensor position (forward and right from robot center)
    sensors['right'] = (sensors['center'][0] + math.cos(math.radians(robot_angle + 90)) * sensor_lateral_offset,
                        sensors['center'][1] + math.sin(math.radians(robot_angle + 90)) * sensor_lateral_offset)
    
    # Calculate left_forward sensor position (more forward and angled left)
    sensors['left_forward'] = (robot_x + math.cos(math.radians(robot_angle + 45)) * sensor_forward_distance * 1.5,
                               robot_y + math.sin(math.radians(robot_angle + 45)) * sensor_forward_distance * 1.5)

    # Calculate right_forward sensor position (more forward and angled right)
    sensors['right_forward'] = (robot_x + math.cos(math.radians(robot_angle - 45)) * sensor_forward_distance * 1.5,
                                robot_y + math.sin(math.radians(robot_angle - 45)) * sensor_forward_distance * 1.5)
    
    return sensors

def sense_line(sensor_positions):
    """Reads the state (on/off line) for all sensors."""
    states = {}
    for name, pos in sensor_positions.items():
        color = get_pixel_color(pos[0], pos[1])
        states[name] = is_on_line(color)
    return states

def draw_sensors_debug(sensor_data):
    """Draws sensor circles and their states for debugging."""
    sensor_radius = 6
    for name, (pos, active) in sensor_data.items():
        color = SENSOR_COLOR_ACTIVE if active else SENSOR_COLOR_PASSIVE
        pygame.draw.circle(WIN, color, (int(pos[0]), int(pos[1])), sensor_radius)

        text_surface = font.render(f"{name[0].upper()}:{'T' if active else 'F'}", True, DEBUG_TEXT_COLOR)
        WIN.blit(text_surface, (int(pos[0]) + sensor_radius + 2, int(pos[1]) - sensor_radius))

def decide_robot_action(sensor_states):
    """Determines robot's turn and speed based on sensor readings."""
    global ROBOT_MODE, LOST_LINE_COUNTER

    turn_angle = 0
    current_speed = BASE_ROBOT_SPEED
    
    # Check if any sensor is on the line
    any_sensor_on_line = any(sensor_states.values())

    if ROBOT_MODE == "FOLLOW_LINE":
        if not any_sensor_on_line:
            # All sensors off line, means we've lost it
            ROBOT_MODE = "LOST_LINE_SEARCH"
            LOST_LINE_COUNTER = 0 # Reset counter when entering search mode
            current_speed = 0 # Stop movement during search
            print("MODE: Lost line from FOLLOW_LINE, entering search.")
        elif sensor_states['center']:
            # Center sensor is on line, apply proportional control
            # Sum of weighted sensor states to calculate steering error
            steering_error = sum(SENSOR_WEIGHTS[s] for s in sensor_states if sensor_states[s])
            turn_angle = steering_error * TURN_RATE # Scale by TURN_RATE
            
            # Clamp turn_angle to prevent excessively sharp turns
            turn_angle = max(-TURN_RATE * 3, min(TURN_RATE * 3, turn_angle))
            LOST_LINE_COUNTER = 0 # Reset counter if line found
        else:
            # Center sensor is off, but others might be on. Prioritize getting center back.
            if sensor_states['left'] and not sensor_states['right']:
                turn_angle = -TURN_RATE * 1.5 # Turn harder left
            elif sensor_states['right'] and not sensor_states['left']:
                turn_angle = TURN_RATE * 1.5 # Turn harder right
            elif sensor_states['left_forward'] and not sensor_states['right_forward']:
                # Approaching a left corner/sharp bend
                turn_angle = -TURN_RATE * 2 # Even harder left
            elif sensor_states['right_forward'] and not sensor_states['left_forward']:
                # Approaching a right corner/sharp bend
                turn_angle = TURN_RATE * 2 # Even harder right
            else:
                # If only side sensors are on, or a mix, still try to use weighted average
                steering_error = sum(SENSOR_WEIGHTS[s] for s in sensor_states if sensor_states[s])
                turn_angle = steering_error * TURN_RATE
                turn_angle = max(-TURN_RATE * 3, min(TURN_RATE * 3, turn_angle))
            LOST_LINE_COUNTER = 0


    elif ROBOT_MODE == "LOST_LINE_SEARCH":
        current_speed = 0 # No forward movement during search
        LOST_LINE_COUNTER += 1

        # Oscillate left and right to find the line
        # Turns right for first half of MAX_LOST_TIME_FRAMES_for_oscillation, then left for second half
        # Let's make it more of a continuous sweep
        if LOST_LINE_COUNTER % (MAX_LOST_TIME_FRAMES / 2) < (MAX_LOST_TIME_FRAMES / 4):
            turn_angle = TURN_RATE * 1.5 # Turn one direction
        else:
            turn_angle = -TURN_RATE * 1.5 # Turn the other direction
        
        if any_sensor_on_line:
            ROBOT_MODE = "FOLLOW_LINE"
            LOST_LINE_COUNTER = 0
            print("MODE: Found line during search, resuming FOLLOW_LINE.")
        
        if LOST_LINE_COUNTER > MAX_LOST_TIME_FRAMES:
            # If line isn't found after maximum search time, stop
            print("Lost line for too long, stopping simulation.")
            pygame.quit()
            exit() # Exit the program

    # Debug output
    print(f"Mode: {ROBOT_MODE}, States: {sensor_states}, Turn: {turn_angle:.2f}, Speed: {current_speed:.2f}")
    print("-" * 30)

    return turn_angle, current_speed

# --- Main Simulation Loop ---
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 1. Clear screen and draw track
    WIN.fill(WHITE)
    draw_track()

    # 2. Get sensor readings
    current_sensor_positions = calculate_sensor_positions(robot_pos[0], robot_pos[1], robot_angle)
    current_sensor_states = sense_line(current_sensor_positions)

    # 3. Decide robot's action (turn and speed)
    turn, speed = decide_robot_action(current_sensor_states)

    # 4. Update robot's position and angle
    robot_angle += turn
    robot_angle %= 360 # Keep angle between 0 and 359

    robot_pos[0] += math.cos(math.radians(robot_angle)) * speed
    robot_pos[1] += math.sin(math.radians(robot_angle)) * speed

    # 5. Keep robot within screen bounds (prevents crashes from get_pixel_color)
    robot_pos[0] = max(0, min(WIDTH - 1, robot_pos[0]))
    robot_pos[1] = max(0, min(HEIGHT - 1, robot_pos[1]))

    # 6. Draw robot and sensors
    draw_robot(robot_pos[0], robot_pos[1], robot_angle)
    # Pass individual sensor positions AND their active state for drawing debug info
    sensor_data_for_drawing = {name: (pos, current_sensor_states[name]) for name, pos in current_sensor_positions.items()}
    draw_sensors_debug(sensor_data_for_drawing)

    # 7. Update display
    pygame.display.flip()

    # 8. Control frame rate
    clock.tick(FPS)

pygame.quit()