# Dependencies
import argparse
import logging
import os
import shutil

import numpy as np

import rava_utils


def main():
    # Set up the logging.
    logging.basicConfig(
        level=logging.INFO,
        format="RevueAVAssistant: %(asctime)s - %(levelname)s - %(message)s",
    )

    # Set up the arguments and parse it.
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=str, help='Project name, e.g. "revue_2022".')
    parser.add_argument("--force", action='store_true', help='Force the processing of all songs. (Default: False)')
    
    args = parser.parse_args()
    assert args.project is not None, "--project name not given."
    assert os.path.exists(args.project), f"The folder {args.project} does not exist. Please copy revue_template and populate the <project>/lyrics/00_raw/ folder."

    if args.force:
        logging.info('Force flag set - removing 02 and 03 completely. Be aware of QLab not pointing to the correct files anymore.')
        shutil.rmtree(os.path.join(args.project, 'lyrics', '02_pptx'))
        shutil.rmtree(os.path.join(args.project, 'lyrics', '03_png'))

        #Make the folders again.
        os.makedirs(os.path.join(args.project, 'lyrics', '02_pptx'))
        os.makedirs(os.path.join(args.project, 'lyrics', '03_png'))
        print('')

    #Find the tex files in the folder.
    raw_paths = sorted(rava_utils.find_raw_lyrics(args.project))

    if len(raw_paths) == 0:
        logging.info(f'No files found in {args.project}/lyrics/00_raw. Quitting.')
        return

    for p_00 in raw_paths:
        #p_00 is the raw path, p_01 is the .txt path, p_02 is the .pptx path, p_03 is the .png folder path.
        song = os.path.basename(p_00).split('.')[0]

        logging.info(f'{song}: processing...')
        p_01 = os.path.join(f'./{args.project}/lyrics/', '01_preprocessed', f'{song}.txt')
        p_02 = os.path.join(f'./{args.project}/lyrics/', '02_pptx', f'{song}.pptx')
        p_03 = os.path.join(f'./{args.project}/lyrics/', '03_png', f'{song}/')

        #If p_01 exists, skip.
        if os.path.exists(p_01):
            logging.info(f'{song}: 00 -> 01 skipped, preprocessed song already exists.')
        elif p_00.endswith('.txt'):
            #If the file is already a .txt file, just copy it.
            shutil.copy(p_00, p_01)
        else:
            rtrn = rava_utils.preprocess_tex(path_in = p_00, path_out = p_01, name = song)
            if rtrn:
                logging.info(f'{song}: 00 -> 01 skipped, no \begin{{obeylines}} and \end{{obeylines}} found.')
            else:
                logging.info(f'{song}: 00 -> 01 done.')

        if os.path.exists(p_02) and os.path.getmtime(p_02) > os.path.getmtime(p_01):
            #If p_02 is newer than p_01, skip.
            logging.info(f'{song}: 01 -> 02 skipped, pptx is up to date.')
        elif not os.path.exists(p_01):
            logging.info(f'{song}: 01 -> 02 skipped. preprocessed file does not exist.')
            logging.info(f'{song}: 02 -> 03 skipped. preprocessed file does not exist.')
            print('')
            continue
        else:
            #Load the preprocessed song.
            song_preprocessed = open(p_01, "r").readlines()

            #Create the pptx.
            rava_utils.create_pptx(song_preprocessed, p_02)
            logging.info(f'{song}: 01 -> 02 done.')

        if os.path.isdir(p_03):
            #Check if all of the pngs in this folder are newer than the pptx.
            png_files = [os.path.join(p_03, x) for x in os.listdir(p_03) if x.endswith('.png')]

            if len(png_files) > 0:
                #Check that all png files are newer than the pptx.
                if all([os.path.getmtime(x) > os.path.getmtime(p_02) for x in png_files]):
                    logging.info(f'{song}: 02 -> 03 skipped. png is already up to date.')
                    print('')
                    continue

        else:
            os.mkdir(p_03)

        #Fill the folder with pngs.
        logging.info(f'{song}: 02 -> 03 creating pngs, please wait...')
        rava_utils.pptx_to_png(p_02, outfolder=p_03)

        #Check the number of pngs in the folder.
        png_files = [os.path.join(p_03, x) for x in os.listdir(p_03) if x.endswith('.png')]

        #Remove pngs that are *older* than the pptx. 
        any_png_removed = False
        for png in png_files:
            if os.path.getmtime(png) < os.path.getmtime(p_02):
                os.remove(png)
                any_png_removed = True

        number_of_png_files = len([os.path.join(p_03, x) for x in os.listdir(p_03) if x.endswith('.png')])
        
        if any_png_removed:
            logging.info(f'{song}: 02 -> 03 removed old pngs. Make sure that QLab is not using them.')

        logging.info(f'{song}: 02 -> 03 complete, {number_of_png_files} pngs written to {p_03}.')

        print('')

    return

if __name__ == "__main__":
    main()
