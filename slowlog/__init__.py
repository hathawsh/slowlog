

def includeme(config):
    """Pyramid hook: activate slowlog tweens if the settings say so."""

    from pyramid.settings import asbool

    if asbool(config.registry.settings.get('slowlog')):
        config.add_tween('slowlog.tween.SlowLogTween')

    if asbool(config.registry.settings.get('framestats')):
        config.add_tween('slowlog.tween.FrameStatsTween')
