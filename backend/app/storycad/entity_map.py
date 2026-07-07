from app.storycad.models import Act, Chapter, Scene, ChapterEdge, Character, CharacterRelation, Theme, ThemeChapter, ChapterRhythm

ENTITY_MAP = {
    "acts": Act,
    "chapters": Chapter,
    "scenes": Scene,
    "edges": ChapterEdge,
    "characters": Character,
    "character_relations": CharacterRelation,
    "themes": Theme,
    "theme_chapters": ThemeChapter,
    "rhythms": ChapterRhythm,
}
