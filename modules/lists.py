# -*- coding: UTF-8 -*-
#
#       lists.py
#
#       Copyright 2009-2019 Giuseppe Penone <giuspen@gmail.com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import gtk
import re
import cons, support

TAG_NOCHANGE = "nochange"
TAG_DOSTRIKE = "dostrike"
TAG_UNSTRIKE = "unstrike"

class ListsHandler:
    """Handler of Bulleted and Numbered Lists"""

    def __init__(self, dad):
        """Lists Handler boot"""
        self.dad = dad

    def get_list_type(self, list_num_id):
        """Return List Type from Num Id"""
        if list_num_id > 0:
            return "Numbered"
        if list_num_id < 0:
            return "Bulleted"
        return "Todo"

    def list_handler(self, target_list_num_id, text_buffer=None):
        """Unified Handler of Lists"""
        if not text_buffer: text_buffer = self.dad.curr_buffer
        if text_buffer.get_has_selection():
            iter_start, sel_end = text_buffer.get_selection_bounds()
            end_offset = sel_end.get_offset() - 2
        else:
            end_offset = 0
            iter_start = text_buffer.get_iter_at_mark(text_buffer.get_insert())
        new_par_offset = -1
        leading_num_count = []
        while new_par_offset < end_offset:
            #print new_par_offset, end_offset
            iter_start, iter_end = self.get_paragraph_iters(text_buffer=text_buffer, force_iter=iter_start)
            if not iter_start:
                # empty line
                if not leading_num_count:
                    # this is the first iteration
                    iter_start = text_buffer.get_iter_at_mark(text_buffer.get_insert())
                    if target_list_num_id == 0:
                        text_buffer.insert(iter_start, self.dad.chars_todo[0] + cons.CHAR_SPACE)
                    elif target_list_num_id < 0:
                        text_buffer.insert(iter_start, self.dad.chars_listbul[0] + cons.CHAR_SPACE)
                    else:
                        text_buffer.insert(iter_start, "1. ")
                break
            list_info = self.get_paragraph_list_info(iter_start)
            #print list_info
            if list_info and iter_start.get_offset() != list_info["startoffs"]:
                new_par_offset = iter_end.get_offset()
            else:
                iter_start, iter_end, chars_rm = self.list_check_n_remove_old_list_type_leading(iter_start, iter_end, text_buffer)
                end_offset -= chars_rm
                if not list_info or self.get_list_type(list_info["num"]) != self.get_list_type(target_list_num_id):
                    # the target list type differs from this paragraph list type
                    while support.get_next_chars_from_iter_are(iter_start, [3*cons.CHAR_SPACE]):
                        iter_start.forward_chars(3)
                    if target_list_num_id == 0:
                        new_par_offset = iter_end.get_offset() + 2
                        end_offset += 2
                        text_buffer.insert(iter_start, self.dad.chars_todo[0] + cons.CHAR_SPACE)
                    elif target_list_num_id < 0:
                        new_par_offset = iter_end.get_offset() + 2
                        end_offset += 2
                        if not list_info: bull_idx = 0
                        else: bull_idx = list_info["level"] % len(self.dad.chars_listbul)
                        text_buffer.insert(iter_start, self.dad.chars_listbul[bull_idx] + cons.CHAR_SPACE)
                    else:
                        if not list_info:
                            index = 0
                            if not leading_num_count:
                                leading_num_count = [[0, 1]]
                            else:
                                leading_num_count = [[0, leading_num_count[0][1]+1]]
                        else:
                            level = list_info["level"]
                            index = level % cons.NUM_CHARS_LISTNUM
                            if not leading_num_count:
                                leading_num_count = [[level, 1]]
                            else:
                                while True:
                                    if level == leading_num_count[-1][0]:
                                        leading_num_count[-1][1] += 1
                                        break
                                    if level > leading_num_count[-1][0]:
                                        leading_num_count.append([level, 1])
                                        break
                                    if len(leading_num_count) == 1:
                                        leading_num_count = [[level, 1]]
                                        break
                                    del leading_num_count[-1]
                        leading_str = str(leading_num_count[-1][1]) + cons.CHARS_LISTNUM[index] + cons.CHAR_SPACE
                        new_par_offset = iter_end.get_offset() + len(leading_str)
                        end_offset += len(leading_str)
                        text_buffer.insert(iter_start, leading_str)
                else: new_par_offset = iter_end.get_offset()
            iter_start = text_buffer.get_iter_at_offset(new_par_offset+1)
            if not iter_start: break

    def list_check_n_remove_old_list_type_leading(self, iter_start, iter_end, text_buffer):
        """Clean List Start Characters"""
        start_offset = iter_start.get_offset()
        end_offset = iter_end.get_offset()
        list_info = self.get_paragraph_list_info(iter_start)
        if list_info:
            leading_chars_num = self.get_leading_chars_num(list_info["num"])
            start_offset += 3*list_info["level"]
            iter_start = text_buffer.get_iter_at_offset(start_offset)
            iter_end = iter_start.copy()
            iter_end.forward_chars(leading_chars_num)
            text_buffer.delete(iter_start, iter_end)
            end_offset -= leading_chars_num
        else:
            leading_chars_num = 0
        iter_start = text_buffer.get_iter_at_offset(start_offset)
        iter_end = text_buffer.get_iter_at_offset(end_offset)
        return iter_start, iter_end, leading_chars_num

    def get_leading_chars_num(self, list_info_num):
        """Get Number of Leading Chars from the List Num"""
        if list_info_num > 0: return len("%s. " % list_info_num)
        return 2

    def list_get_number_n_level(self, iter_first_paragraph):
        """Number < 0 if bulleted list, > 0 if numbered list, 0 if TODO list, None if not a list"""
        iter_start = iter_first_paragraph.copy()
        level = 0
        while iter_start:
            char = iter_start.get_char()
            if char in self.dad.chars_listbul:
                if iter_start.forward_char() and iter_start.get_char() == cons.CHAR_SPACE:
                    num = (self.dad.chars_listbul.index(char) + 1)*(-1)
                    return {"num":num, "level":level, "aux":None}
                break
            if char in self.dad.chars_todo:
                if iter_start.forward_char() and iter_start.get_char() == cons.CHAR_SPACE:
                    return {"num":0, "level":level, "aux":None}
                break
            if char == cons.CHAR_SPACE:
                if support.get_next_chars_from_iter_are(iter_start, [3*cons.CHAR_SPACE]):
                    iter_start.forward_chars(3)
                    level += 1
                else:
                    break
            else:
                match = re.match('[1-9]', char)
                if not match:
                    break
                number_str = char
                while iter_start.forward_char() and re.match('[0-9]', iter_start.get_char()):
                    number_str += iter_start.get_char()
                char = iter_start.get_char()
                if char in cons.CHARS_LISTNUM and iter_start.forward_char() and iter_start.get_char() == cons.CHAR_SPACE:
                    num = int(number_str)
                    aux = cons.CHARS_LISTNUM.index(char)
                    return {"num":num, "level":level, "aux":aux}
                break
        return {"num":None, "level":level, "aux":None}

    def get_multiline_list_element_end_offset(self, curr_iter, list_info):
        """Get the list end offset"""
        iter_start = curr_iter.copy()
        if iter_start.get_char() == cons.CHAR_NEWLINE:
            if not iter_start.forward_char():
                # the end of buffer is also the list end
                return iter_start.get_offset()
        else:
            if not self.char_iter_forward_to_newline(iter_start) or not iter_start.forward_char():
                # the end of buffer is also the list end
                return iter_start.get_offset()
        number_n_level = self.list_get_number_n_level(iter_start)
        #print number_n_level
        if number_n_level["num"] == None and number_n_level["level"] == list_info["level"]+1:
            # multiline indentation
            return self.get_multiline_list_element_end_offset(iter_start, list_info)
        return iter_start.get_offset()-1

    def get_prev_list_info_on_level(self, iter_start, level):
        """Given a level check for previous list number on the level or None"""
        ret_val = None
        while iter_start:
            if not self.char_iter_backward_to_newline(iter_start):
                break
            list_info = self.get_paragraph_list_info(iter_start)
            if not list_info:
                break
            if list_info["level"] < level:
                break
            if list_info["level"] == level:
                ret_val = list_info
                break
        return ret_val

    def get_next_list_info_on_level(self, iter_start, level):
        """Given a level check for next list number on the level or None"""
        ret_val = None
        while iter_start:
            if not self.char_iter_forward_to_newline(iter_start):
                break
            list_info = self.get_paragraph_list_info(iter_start)
            if not list_info:
                break
            if list_info["level"] == level:
                ret_val = list_info
                break
        return ret_val

    def get_paragraph_list_info(self, iter_start_orig):
        """Returns a dictionary indicating List Element Number, List Level and List Element Start Offset"""
        buffer_start = False
        iter_start = iter_start_orig.copy()
        # let's search for the paragraph start
        if iter_start.get_char() == cons.CHAR_NEWLINE:
            if not iter_start.backward_char(): buffer_start = True # if we are exactly on the paragraph end
        if not buffer_start:
            while iter_start:
                if iter_start.get_char() == cons.CHAR_NEWLINE: break # we got the previous paragraph start
                elif not iter_start.backward_char():
                    buffer_start = True
                    break # we reached the buffer start
        if not buffer_start: iter_start.forward_char()
        # get the number of the paragraph starting with iter_start
        number_n_level = self.list_get_number_n_level(iter_start)
        curr_level = number_n_level["level"]
        if number_n_level["num"] != None:
            return {"num":number_n_level["num"],
                    "level":curr_level,
                    "aux":number_n_level["aux"],
                    "startoffs":iter_start.get_offset()}
        #print number_n_level
        if not buffer_start and curr_level > 0:
            # may be a list paragraph but after a shift+return
            iter_start.backward_char()
            list_info = self.get_paragraph_list_info(iter_start)
            #print list_info
            if list_info:
                if (list_info["num"] != None and list_info["level"] == (curr_level-1))\
                or (list_info["num"] == None and list_info["level"] == curr_level):
                    return list_info
        return None # this paragraph is not a list

    def get_paragraph_iters(self, text_buffer=None, force_iter=None):
        """Generates and Returns two iters indicating the paragraph bounds"""
        if not text_buffer: text_buffer = self.dad.curr_buffer
        if not force_iter and text_buffer.get_has_selection():
            iter_start, iter_end = text_buffer.get_selection_bounds() # there's a selection
        else:
            # There's not a selection/iter forced
            if not force_iter: iter_start = text_buffer.get_iter_at_mark(text_buffer.get_insert())
            else: iter_start = force_iter.copy()
            iter_end = iter_start.copy()
            if iter_start.get_char() == cons.CHAR_NEWLINE:
                # we're upon a row end
                if not iter_start.backward_char(): return (None, None)
                if iter_start.get_char() == cons.CHAR_NEWLINE: return (None, None)
        while iter_end != None:
            char = iter_end.get_char()
            if char == cons.CHAR_NEWLINE: break # we got it
            elif not iter_end.forward_char(): break # we reached the buffer end
        while iter_start != None:
            char = iter_start.get_char()
            if char == cons.CHAR_NEWLINE: # we got it
                iter_start.forward_char() # step forward to the beginning of the new line
                break
            elif not iter_start.backward_char(): break # we reached the buffer start
        return (iter_start, iter_end)

    def is_list_todo_beginning(self, square_bracket_open_iter):
        """Check if ☐ or ☑ or ☒"""
        if square_bracket_open_iter.get_char() in self.dad.chars_todo:
            list_info = self.get_paragraph_list_info(square_bracket_open_iter)
            if list_info and list_info["num"] == 0:
                return True
        return False

    def todo_list_rotate_status(self, todo_char_iter, text_buffer):
        """Rotate status between ☐ and ☑ and ☒"""
        iter_offset = todo_char_iter.get_offset()
        (start_index, end_index) = self.get_start_end_of_checkbox(text_buffer, todo_char_iter)
        if todo_char_iter.get_char() == self.dad.chars_todo[0]:
            text_buffer.delete(todo_char_iter, text_buffer.get_iter_at_offset(iter_offset+1))
            text_buffer.insert(text_buffer.get_iter_at_offset(iter_offset), self.dad.chars_todo[1])
            self.strike_through_checkbox_text(TAG_DOSTRIKE, start_index, end_index, text_buffer)
        elif todo_char_iter.get_char() == self.dad.chars_todo[1]:
            text_buffer.delete(todo_char_iter, text_buffer.get_iter_at_offset(iter_offset+1))
            text_buffer.insert(text_buffer.get_iter_at_offset(iter_offset), self.dad.chars_todo[2])
            self.strike_through_checkbox_text(TAG_NOCHANGE, start_index, end_index, text_buffer)
        elif todo_char_iter.get_char() == self.dad.chars_todo[2]:
            text_buffer.delete(todo_char_iter, text_buffer.get_iter_at_offset(iter_offset+1))
            text_buffer.insert(text_buffer.get_iter_at_offset(iter_offset), self.dad.chars_todo[0])
            self.strike_through_checkbox_text(TAG_UNSTRIKE, start_index, end_index, text_buffer)

    def get_start_end_of_checkbox(self, buffer, char_iter):
        """Find the start and end of a line/paragraph after a checkbox to strike through/remove the strike through"""
        line_no = char_iter.get_line()
        start = buffer.get_iter_at_line(line_no)
        checkbox_from_line_start = 0
        while start.get_char() not in self.dad.chars_todo:
            start.set_offset(start.get_offset() + 1)
            checkbox_from_line_start += 1
        start.set_offset(start.get_offset() + 2)
        if line_no < buffer.get_line_count() - 1:
            line_no = self.get_line_no_where_para_stops(buffer, line_no, checkbox_from_line_start+3)
            end = buffer.get_iter_at_line(line_no + 1)
            end.set_offset(end.get_offset() - 1)
        else:
            end = buffer.get_end_iter()
        return start.get_offset(), end.get_offset()

    def get_line_no_where_para_stops(self, buffer, line_no, must_be_white_space):
        """A checkbox paragraph can extend over several lines, which is the last one?"""
        while True:
            line_no += 1
            # is there a next line?
            if line_no >= buffer.get_line_count():
                return line_no - 1
            # does the next line have enough chars?
            start_iter = buffer.get_iter_at_line(line_no)
            if start_iter.get_chars_in_line() <= must_be_white_space:
                return line_no - 1
            # are all of the first must_be_white_space char chars white space?
            end_iter = buffer.get_iter_at_line(line_no)
            end_iter.set_offset(end_iter.get_offset() + must_be_white_space)
            slice = buffer.get_slice(start_iter, end_iter)
            if len(slice) > slice.count(" "):
                return line_no - 1
            # does the line contain a checkbox?
            if line_no < buffer.get_line_count() - 1:
                end_iter = buffer.get_iter_at_line(line_no + 1)
                end_iter.set_offset(end_iter.get_offset() - 1)
            else:
                end_iter = buffer.get_end_iter()
            slice = buffer.get_slice(start_iter, end_iter)
            for t in self.dad.chars_todo:
                if t in slice:
                    return line_no - 1

    def strike_through_checkbox_text(self, doit, start_index, end_index, buffer):
        """Change the text from start_index to end_index to strike through/remove it, depending on the value of
        parameter doit"""
        if doit == TAG_NOCHANGE:
            return
        start_iter = buffer.get_start_iter()
        start_iter.set_offset(start_index)
        end_iter = buffer.get_end_iter()
        end_iter.set_offset(end_index)
        self.dad.apply_tag(cons.TAG_STRIKETHROUGH, cons.TAG_PROP_TRUE, start_iter, end_iter, buffer)

    def char_iter_forward_to_newline(self, char_iter):
        """Forwards char iter to line end"""
        if not char_iter.forward_char(): return False
        while char_iter.get_char() != cons.CHAR_NEWLINE:
            if not char_iter.forward_char(): return False
        return True

    def char_iter_backward_to_newline(self, char_iter):
        """Backwards char iter to line start"""
        if not char_iter.backward_char(): return False
        while char_iter.get_char() != cons.CHAR_NEWLINE:
            if not char_iter.backward_char(): return False
        return True

    def todo_lists_old_to_new_conversion(self, text_buffer):
        """Conversion of todo lists from old to new type for a node"""
        curr_iter = text_buffer.get_start_iter()
        keep_cleaning = False
        first_line = True
        while curr_iter:
            fw_needed = True
            if first_line or curr_iter.get_char() == cons.CHAR_NEWLINE and curr_iter.forward_char():
                first_line = False
                if keep_cleaning:
                    iter_bis = curr_iter.copy()
                    if iter_bis.get_char() == cons.CHAR_SPACE and iter_bis.forward_char()\
                    and iter_bis.get_char() == cons.CHAR_SPACE and iter_bis.forward_char()\
                    and iter_bis.get_char() == cons.CHAR_SPACE:
                        no_stop = self.char_iter_forward_to_newline(curr_iter)
                        text_buffer.remove_all_tags(iter_bis, curr_iter)
                        if no_stop: continue
                        else: break
                    else: keep_cleaning = False
                if curr_iter.get_char() == cons.CHAR_SQ_BR_OPEN and curr_iter.forward_char()\
                and curr_iter.get_char() in [cons.CHAR_SPACE, "X"]:
                    middle_char = curr_iter.get_char()
                    if curr_iter.forward_char() and curr_iter.get_char() == cons.CHAR_SQ_BR_CLOSE\
                    and curr_iter.forward_char():
                        first_iter = curr_iter.copy()
                        first_iter.backward_chars(3)
                        iter_offset = first_iter.get_offset()
                        text_buffer.delete(first_iter, curr_iter)
                        todo_char = self.dad.chars_todo[0] if middle_char == cons.CHAR_SPACE else self.dad.chars_todo[1]
                        text_buffer.insert(text_buffer.get_iter_at_offset(iter_offset), todo_char)
                        curr_iter = text_buffer.get_iter_at_offset(iter_offset)
                        if middle_char != cons.CHAR_SPACE:
                            first_iter = curr_iter.copy()
                            no_stop = self.char_iter_forward_to_newline(curr_iter)
                            #print "%s(%s),%s(%s)" % (first_iter.get_char(), first_iter.get_offset(), curr_iter.get_char(), curr_iter.get_offset())
                            text_buffer.remove_all_tags(first_iter, curr_iter)
                            keep_cleaning = True
                            if no_stop: continue
                            else: break
                else: fw_needed = False
            if fw_needed and not self.char_iter_forward_to_newline(curr_iter): break
