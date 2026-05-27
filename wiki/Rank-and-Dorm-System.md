# Rank and Dorm System

The game evaluates the player's performance to assign a **Duelist Rank** and **Dorm Assignment**. This evaluation happens periodically (e.g., during Dorm Switch Exams).

## Rank Evaluation Logic

`calculate_player_rank` (0x0809FF00) determines the rank based on four primary metrics:

1. **Card Collection Count**: `get_card_collection_count` (0x080E57E0)
2. **Written Exam High Score**: `get_written_exam_high_score` (0x080E6B4C)
3. **Timed Duel Clear Count**: `get_timed_duel_clear_count` (0x080E6C1C)
4. **Duel Win Count**: `get_duel_stat_by_type(player_id, STAT_WINS)` (0x080E6250)

### Rank Requirements (Approximate)

| Rank ID | Title | Requirement Snippets |
|---------|-------|----------------------|
| 1 | King of Games | 100% Cards, 100 Written, 120+ Timed, 200+ Wins, win against all key NPCs |
| 4 | Prince of Games | 100% Cards, 100 Written, 80+ Timed, 100+ Wins |
| 10 | Rookie | 10+ Wins |
| 11 | Novice | 1+ Wins |
| 13 | Dropout Boy | Default rank |

## Dorm Assignment

`set_player_dorm_flags` (0x080A0164) updates the player's dorm:
- **0**: Slifer Red
- **1**: Obelisk Blue
- **2**: Ra Yellow

This function also updates the "Occult Duelist" status for related NPCs (Alexis, Jaden, Chazz), which likely controls their appearance or interaction logic in the overworld.

## Notification State Machine

`rank_and_dorm_evaluation_sm` (0x080A1F30) manages the sequence of:
1. Calculating new rank.
2. Checking if rank changed.
3. Showing rank/dorm change notifications.
4. Saving the result.

## Key Functions

| Address | Name | Role |
|---------|------|------|
| `0x0809FF00` | `calculate_player_rank` | Core rank calculation logic |
| `0x080A1F30` | `rank_and_dorm_evaluation_sm` | Eval flow state machine |
| `0x080A0408` | `set_player_rank_bits` | Updates rank bits in EWRAM |
| `0x080A0164` | `set_player_dorm_flags` | Updates dorm flags in EWRAM |
| `0x080BB77C` | `get_rank_title` | Rank ID -> String lookup |
| `0x080BB7A0` | `get_dorm_text` | Dorm ID -> String lookup |
| `0x080A3CF8` | `show_rank_change_notification` | Displays "Your title is now..." |
| `0x080A3D68` | `show_dorm_change_notification` | Displays "Your dorm is now..." |
