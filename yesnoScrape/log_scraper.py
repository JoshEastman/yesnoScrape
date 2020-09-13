from time import sleep

import pyautogui
import pytesseract
from PIL import Image, ImageFilter


class LogScaperException(Exception):
    pass


class LogScraper:
    def __init__(self, ally_names=[], enemy_names=[]):
        self.ally_names = ally_names
        self.enemy_names = enemy_names
        self.current_log = ''
        self.previous_log = ''
        self.button_locations = {}
        self.regions = {}
        self.text_logs = ""
        self.log_count = 0
        self.current_page = 0
        self.total_pages = 0
        self.set_regions()

    def get_all_logs(self, only_ally=False):
        if only_ally:
            pyautogui.click(pyautogui.center(self.button_locations['ally']))

        self.current_page, self.total_pages = self._get_page_numbers()
        for i in range(self.total_pages):
            self.get_logs_from_page()
            self.go_to_next_page()
        self._write_to_file()

    def get_logs_from_page(self):
        bottom_of_page = False
        while not bottom_of_page:
            new_log = self.get_log()
            # check if bottom of page
            curr = ''.join(e for e in self.current_log[0:25].lower() if e.isalnum())
            prev = ''.join(e for e in self.previous_log[0:25].lower() if e.isalnum())
            if curr == prev:
                bottom_of_page = True
                continue
            else:
                self.text_logs = self.text_logs + new_log
                self.scroll_down()
        self.current_page += 1

    def get_log(self):
        raw_log = self.take_screenshot_of_log()
        new_log = self.read_log(raw_log)
        self.previous_log = self.current_log
        self.current_log = new_log
        return new_log

    def read_log(self, raw_log):
        # Fuck with new log colors so that it can be more easily read
        readable_log = self._make_log_text_parsable(raw_log)
        # convert new_log into text
        log_text = pytesseract.image_to_string(readable_log)
        # return new_log_text
        return log_text

    def take_screenshot_of_log(self):
        # take screenshot with log_coords
        new_screenshot = pyautogui.screenshot(region=self.regions['log'])
        self.log_count += 1
        # return the image
        return new_screenshot

    def scroll_down(self):
        log_x = self.regions['log'][0] + (self.regions['log'][2] / 2)
        log_y = self.regions['log'][1] + (self.regions['log'][3] * 0.9)
        pyautogui.moveTo((log_x, log_y))
        pyautogui.dragTo(log_x, self.regions['log'][1]+10, 0.5, button='left')
        pyautogui.click()
        sleep(1) # wait for click effect to go away

    def go_to_next_page(self):
        # click next page buttons
        next_x, next_y = pyautogui.center(self.button_locations['next_page'])
        pyautogui.moveTo(x=next_x, y=next_y)
        pyautogui.click()
        sleep(1)

    def set_regions(self):
        # First find the button_locations
        self._set_button_locations()
        # Then set the regions based on that.
        self._set_log_region()
        self._set_page_number_region()

    def _set_button_locations(self):
        # locate all, summon, back and next page (maybe do this on init?)
        all_loc = pyautogui.locateOnScreen('./yesnoScrape/images/all_dir_button.png')
        summon_loc = pyautogui.locateOnScreen('./yesnoScrape/images/summon_dir_button.png')
        back_loc = pyautogui.locateOnScreen('./yesnoScrape/images/back_button.png')
        next_loc = pyautogui.locateOnScreen('./yesnoScrape/images/next_page_button.png')
        ally_loc = pyautogui.locateOnScreen('./yesnoScrape/images/ally_dir_button.png')

        if not all_loc or not summon_loc or not back_loc or not next_loc:
            print('Could not find one of the buttons. Crashing and burning in a storm of hellfire and brimstone.')
            print(f'all: {all_loc} | summon: {summon_loc} | back: {back_loc} | next: {next_loc}')
            raise LogScaperException()

        # set the self.button_locations variable
        self.button_locations['all'] = all_loc
        self.button_locations['summon'] = summon_loc
        self.button_locations['next_page'] = next_loc
        self.button_locations['back_button'] = back_loc
        self.button_locations['ally'] = ally_loc

    def _set_log_region(self):
        # Using the all button, summon button, and next page button, get the coords needed to screenshot the logs
        left = self.button_locations['all'].left
        top = self.button_locations['all'].top + self.button_locations['all'].height
        width = self.button_locations['summon'].left + self.button_locations['summon'].width - left
        height = self.button_locations['next_page'].top - top

        self.regions['log'] = (left, top, width, height)

    def _set_page_number_region(self):
        # Use coords of back & next page to take screenshot of where page numbers variable
        left = self.button_locations['back_button'].left + self.button_locations['back_button'].width
        top = self.button_locations['back_button'].top
        width = self.button_locations['next_page'].left - left
        height = self.button_locations['back_button'].height
        self.regions['page_numbers'] = (left, top, width, height)

    def _get_page_numbers(self):
        # take new_screenshot of current page number
        page_numbers_image = pyautogui.screenshot(region=(self.regions['page_numbers']))
        # parse for page numbers
        current_page_raw, total_pages_raw = self._page_numbers_from_image(page_numbers_image)
        try:
            current_page = int(current_page_raw)
            total_pages = int(total_pages_raw)
        except ValueError:
            print(f'Got a page number that could not be turned into an int. ({current_page_raw}/{total_pages_raw})')
            raise LogScaperException(f'Got a page number that could not be turned into an int. \
                                        ({current_page_raw}/{total_pages_raw})')
        return current_page, total_pages

    def _make_log_text_parsable(self, log_image):
        # Fuck with new log colors so that it can be more easily read
        log_pix = log_image.load()
        for y in range(log_image.size[1]):
            for x in range(log_image.size[0]):
                log_pix[x, y] = self._check_if_target_values(log_pix[x, y])
        return log_image

    def _check_if_target_values(self, rgb):
        red, green, blue = rgb

        if ((red < 56 or red > 96) or (green < 47 or green > 90) or (blue < 40 or blue > 78)) and \
           ((red < 100 or red > 115) or (green < 89 or green > 105) or (blue < 80 or blue > 100)):
            return (255, 255, 255, 255)
        return (0, 0, 0, 255)

    def _page_numbers_from_image(self, page_numbers_image):
        # Make blurry numbers less blurry so they can be read
        parsable_numbers = page_numbers_image.convert('L')
        page_numbers_raw = pytesseract.image_to_string(parsable_numbers)
        page_numbers = page_numbers_raw.split('\n')[0]
        current_page, total_pages = page_numbers.split('/')
        return current_page, total_pages

    def _write_to_file(self):
        log_file = open("log_text.txt", "a")
        log_file.write(self.text_logs)
        log_file.close()
