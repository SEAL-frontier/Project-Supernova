MODES=('auto','soft','spicy')

def mode(store,user):
    row=store.one('SELECT mode FROM kei_persona_preferences WHERE user=?',(str(user),))
    return row['mode'] if row else 'auto'

def set_mode(store,user,value):
    if value not in MODES:raise ValueError('Chọn auto, soft hoặc spicy.')
    store.execute('INSERT OR REPLACE INTO kei_persona_preferences VALUES (?,?)',(str(user),value))

def prompt(config,store,user):
    chosen=mode(store,user)
    selected=config.get('persona_variants',{}).get(chosen)
    if selected is None:return config['persona']
    return selected+'\nPERSONA MODE: '+chosen+'. This selected persona takes precedence over generic tool style descriptions. soft preserves the previous gentle style; spicy is sharper; auto adapts to the actual conversation.'
