# coding=utf-8

import datetime
import os
import pprint
import copy

import subliminal
from items import get_item
from subzero.subtitle_storage import StoredSubtitlesManager

from subtitlehelpers import force_utf8
from config import config
from helpers import notify_executable, get_title_for_video_metadata, cast_bool, force_unicode
from plex_media import PMSMediaProxy


get_subtitle_storage = lambda: StoredSubtitlesManager(Data, get_item)


def whack_missing_parts(scanned_video_part_map, existing_parts=None):
    """
    cleans out our internal storage's video parts (parts may get updated/deleted/whatever)
    :param existing_parts: optional list of part ids known
    :param scanned_video_part_map: videos to check for
    :return:
    """
    # shortcut

    if "subs" not in Dict:
        return

    if not existing_parts:
        existing_parts = []
        for part in scanned_video_part_map.viewvalues():
            existing_parts.append(str(part.id))

    whacked_parts = False
    for video in scanned_video_part_map.keys():
        video_id = str(video.id)
        if video_id not in Dict["subs"]:
            continue

        parts = Dict["subs"][video_id].keys()

        for part_id in parts:
            part_id = str(part_id)
            if part_id not in existing_parts:
                Log.Info("Whacking part %s in internal storage of video %s (%s, %s)", part_id, video_id,
                         repr(existing_parts), repr(parts))
                del Dict["subs"][video_id][part_id]
                whacked_parts = True

    if whacked_parts:
        Dict.Save()


def store_subtitle_info(scanned_video_part_map, downloaded_subtitles, storage_type, mode="a"):
    """
    stores information about downloaded subtitles in plex's Dict()
    """
    existing_parts = []
    for video, video_subtitles in downloaded_subtitles.items():
        part = scanned_video_part_map[video]
        part_id = str(part.id)
        video_id = str(video.id)
        plex_item = get_item(video_id)
        metadata = video.plexapi_metadata
        title = get_title_for_video_metadata(metadata)

        subtitle_storage = get_subtitle_storage()
        stored_subs = subtitle_storage.load_or_new(plex_item)

        existing_parts.append(part_id)

        stored_any = False
        for subtitle in video_subtitles:
            lang = Locale.Language.Match(subtitle.language.alpha2)
            Log.Debug(u"Adding subtitle to storage: %s, %s, %s" % (video_id, part_id, title))
            ret_val = stored_subs.add(part_id, lang, subtitle, storage_type, mode=mode)

            if ret_val:
                Log.Debug("Subtitle stored")
                stored_any = True

            else:
                Log.Debug("Subtitle already existing in storage")

        if stored_any:
            Log.Debug("Saving subtitle storage for %s" % video_id)
            subtitle_storage.save(stored_subs)

    #if existing_parts:
    #    whack_missing_parts(scanned_video_part_map, existing_parts=existing_parts)


def reset_storage(key):
    """
    resets the Dict[key] storage, thanks to https://docs.google.com/document/d/1hhLjV1pI-TA5y91TiJq64BdgKwdLnFt4hWgeOqpz1NA/edit#
    We can't use the nice Plex interface for this, as it calls get multiple times before set
    #Plex[":/plugins/*/prefs"].set("com.plexapp.agents.subzero", "reset_storage", False)
    """

    Log.Debug("resetting storage")
    Dict[key] = {}
    Dict.Save()


def log_storage(key):
    if key in Dict:
        Log.Debug(pprint.pformat(Dict[key]))


def save_subtitles_to_file(subtitles):
    fld_custom = Prefs["subtitles.save.subFolder.Custom"].strip() \
        if Prefs["subtitles.save.subFolder.Custom"] else None

    for video, video_subtitles in subtitles.items():
        if not video_subtitles:
            continue

        fld = None
        if fld_custom or Prefs["subtitles.save.subFolder"] != "current folder":
            # specific subFolder requested, create it if it doesn't exist
            fld_base = os.path.split(video.name)[0]
            if fld_custom:
                if fld_custom.startswith("/"):
                    # absolute folder
                    fld = fld_custom
                else:
                    fld = os.path.join(fld_base, fld_custom)
            else:
                fld = os.path.join(fld_base, Prefs["subtitles.save.subFolder"])
            fld = force_unicode(fld)
            if not os.path.exists(fld):
                os.makedirs(fld)
        subliminal.api.save_subtitles(video, video_subtitles, directory=fld, single=cast_bool(Prefs['subtitles.only_one']),
                                      encode_with=force_utf8 if config.enforce_encoding else None,
                                      chmod=config.chmod, forced_tag=config.forced_only, path_decoder=force_unicode)
    return True


def save_subtitles_to_metadata(videos, subtitles):
    for video, video_subtitles in subtitles.items():
        mediaPart = videos[video]
        for subtitle in video_subtitles:
            content = force_utf8(subtitle.text) if config.enforce_encoding else subtitle.content

            if not isinstance(mediaPart, Framework.api.agentkit.MediaPart):
                # we're being handed a Plex.py model instance here, not an internal PMS MediaPart object.
                # get the correct one
                mp = PMSMediaProxy(video.id).get_part()
            else:
                mp = mediaPart
            mp.subtitles[Locale.Language.Match(subtitle.language.alpha2)][subtitle.id] = Proxy.Media(content, ext="srt")
    return True


def save_subtitles(scanned_video_part_map, downloaded_subtitles, mode="a"):
    meta_fallback = False
    save_successful = False
    storage = "metadata"
    if Prefs['subtitles.save.filesystem']:
        storage = "filesystem"
        try:
            Log.Debug("Using filesystem as subtitle storage")
            save_subtitles_to_file(downloaded_subtitles)
        except OSError:
            if Prefs["subtitles.save.metadata_fallback"]:
                meta_fallback = True
            else:
                raise
        else:
            save_successful = True

    if not Prefs['subtitles.save.filesystem'] or meta_fallback:
        if meta_fallback:
            Log.Debug("Using metadata as subtitle storage, because filesystem storage failed")
        else:
            Log.Debug("Using metadata as subtitle storage")
        save_successful = save_subtitles_to_metadata(scanned_video_part_map, downloaded_subtitles)

    if save_successful and config.notify_executable:
        notify_executable(config.notify_executable, scanned_video_part_map, downloaded_subtitles, storage)

    store_subtitle_info(scanned_video_part_map, downloaded_subtitles, storage, mode=mode)
