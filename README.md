# Pycast

A Python interface to [Vericast](http://http://www.bmat.com/products/vericast/). Vericast is a global music identification service that monitors millions of songs over 2000 radios and televisions across more than 50 countries worldwide.

## Examples

Where is Madonna broadcast more?

    import pycast
    madonna = pycast.Artist('Madonna', 'YOUR_USER_HERE', 'YOUR_KEY_HERE')
    channels = madonna.get_top_channels()
    for channel in channels:
        print channel

What songs were played in "BBC radio 1" last month?

    import pycast
    bbc = pycast.Channel('gb-radio-bbc-radio-1----------01', 'YOUR_USER_HERE', 'YOUR_KEY_HERE')
    songs = bbc.get_top_tracks(period=pycast.month)
    from song in songs:
       print song

What are the most famous artists in BCore label?

    import pycast                                                                                 
    bcore = pycast.Label('BCore', 'YOUR_USER_HERE', 'YOUR_KEY_HERE')
    artists = bcore.get_top_artists(period=pycast.WEEK)
    from artist in artists:
       print artist

What is the weekly chart for tracks?

    import pycast
    import datetime
    chart = pycast.Chart(
        period=pycast.WEEK, toDate=datetime.date(2012, 3, 4),
        'YOUR_USER_HERE', 'YOUR_KEY_HERE')
    tracks = pycast.get_top_tracks()
    for track in tracks:
        print track
