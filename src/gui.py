import valstats as vs
import tkinter as tk
import re
from tkinter import ttk
from tkinter import scrolledtext as stxt
# from tkinter import font as tkfont



class PlaceholderEntry(ttk.Entry):
    def __init__(self, container, placeholder, *args, **kwargs):
        super().__init__(container, *args, style="Placeholder.TEntry", **kwargs)
        self.placeholder = placeholder

        self.insert("0", self.placeholder)
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)
        self.bind("<Escape>", lambda e: container.focus_set())

    def _clear_placeholder(self, e):
        if self["style"] == "Placeholder.TEntry":
            self.delete("0", tk.END)
            self["style"] = "TEntry"

    def _add_placeholder(self, e):
        if not self.get():
            self.insert("0", self.placeholder)
            self["style"] = "Placeholder.TEntry"
    
    def is_empty(self):
        return self["style"] == "Placeholder.TEntry" or not self.get()


class ChapterPrinter(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title("Chapter Printer")
        
        self.puuid: str | None = None
        self.chapterStr: vs.MatchStats | None = None
        self.startTime: int | None = None

        # the container is where we'll stack a bunch of frames
        # on top of each other, then the one we want visible
        # will be raised above the others
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (GTEntryPage, MatchEntryPage, ChaptersPage): # add more pages here
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame

            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("GTEntryPage") # top page

    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        frame = self.frames[page_name]
        frame.tkraise()
    
    def copy_to_clipboard(self, field):
        '''Copy the given field value to the clipboard'''
        self.clipboard_clear()
        self.clipboard_append(field.get("1.0", tk.END).rstrip())


class GTEntryPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        self.riotID: str | None = None
        
        rIDlabel = tk.Label(self, text="Riot ID:")
        rIDlabel.grid(row=1, column=1, pady=10)
        
        self.rIDentry = PlaceholderEntry(self, "username#TAG")
        self.rIDentry.grid(row=1, column=2, pady=10)
        self.rIDentry.bind("<Return>", self._check_RiotID)
        
        buttonEnter = tk.Button(self, text="Enter", command=self._check_RiotID)
        buttonEnter.grid(row=2, column=1, columnspan=2)
        
        self.warningStr = tk.StringVar()
        warningLable = tk.Label(self, textvariable=self.warningStr, width=35, height=0, wraplength=200)
        warningLable.grid(row=3, column=1, columnspan=2, pady=10)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(3, weight=1)
    
    def _check_RiotID(self, e=None):
        if self.rIDentry.is_empty():
            self.warningStr.set("Please enter Riot ID")
            return
        elif self.riotID != self.rIDentry.get().rstrip():
            try:
                username, tagline = vs.str_to_user_gt(self.rIDentry.get())
                self.controller.puuid = vs.gt_to_puuid(username, tagline)
                self.riotID = self.rIDentry.get().rstrip()
            except Exception as e:
                self.warningStr.set(f"Error: {e}")
                return
        self.controller.show_frame("MatchEntryPage")
    
            


class MatchEntryPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        mIDlabel = tk.Label(self, text="Match ID:")
        mIDlabel.grid(row=1, column=1, pady=10)
        
        self.mIDentry = PlaceholderEntry(self, "00000000-0000-0000-0000-000000000000")
        self.mIDentry.grid(row=1, column=2, pady=10)
        self.mIDentry.bind("<Return>", self._lookup_match)
        
        timeLabel = tk.Label(self, text="End of 1st pre-round:")
        timeLabel.grid(row=2, column=1, pady=10)
        
        self.timeEntry = PlaceholderEntry(self, "h:mm:ss / mm:ss / sss")
        self.timeEntry.grid(row=2, column=2, pady=10)
        self.timeEntry.bind("<Return>", self._lookup_match)
        
        buttonBack = tk.Button(self, text="Go back", command=lambda: self.controller.show_frame("GTEntryPage"))
        buttonBack.grid(row=3, column=1)
        
        buttonEnter = tk.Button(self, text="Enter", command=self._lookup_match)
        buttonEnter.grid(row=3, column=2)
        
        self.warningStr = tk.StringVar()
        warningLable = tk.Label(self, textvariable=self.warningStr, width=37, height=0, wraplength=220)
        warningLable.grid(row=4, column=1, columnspan=2, pady=10)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(3, weight=1)
    
    def _lookup_match(self, e=None):
        if self.mIDentry.is_empty():
            self.warningStr.set("Please enter Match ID")
            return
        matchID = self.mIDentry.get().rstrip()
        if not self._verify_match_id_format(matchID):
            self.warningStr.set("Invalid match ID format")
            return
        
        if self.timeEntry.is_empty():
            self.controller.startTime = 60
        else:
            time = self.timeEntry.get().rstrip().split(':')
            for part in time:
                if not part.isnumeric():
                    self.warningStr.set("Invalid time format: non-numeric input")
                    return
                if int(part) < 0:
                    self.warningStr.set("Invalid time format: negative input")
                    return
            if len(time) == 3:
                self.controller.startTime = int(time[0]) * 3600 + int(time[1]) * 60 + int(time[2])
            elif len(time) == 2:
                self.controller.startTime = int(time[0]) * 60 + int(time[1])
            elif len(time) == 1:
                self.controller.startTime = int(time[0])
            else:
                self.warningStr.set("Invalid time format: incorrect segments")
                return
        try:
            tempMatchStats = vs.MatchStats(matchID, self.controller.puuid)
        except Exception as e:
            self.warningStr.set(f"Error: {e}")
            return
        self.controller.matchStats = tempMatchStats
        self.controller.frames["ChaptersPage"].update_text()
        self.controller.show_frame("ChaptersPage")
    
    def _verify_match_id_format(self, match_id):
        pattern = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        return pattern.match(match_id) is not None
    
    def clear_entries(self):
        '''Clears the entries in the match ID entry field and the time entry field'''
        self.mIDentry.delete(0, tk.END)
        self.timeEntry.delete(0, tk.END)

class ChaptersPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        buttonCopy = tk.Button(self, text="Copy to clipboard", command=lambda: controller.copy_to_clipboard(self.textChapters))
        buttonCopy.grid(row=1, column=1)
        
        buttonBack = tk.Button(self, text="New match", command=self._go_back)
        buttonBack.grid(row=1, column=2)
        
        self.textChapters = stxt.ScrolledText(self, width=40, height=10, state="disabled")
        self.textChapters.grid(row=2, column=1, columnspan=2)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(3, weight=1)

    def update_text(self):
        '''Updates the text in the textChapters widget with the chapters obtained from the matchStats object'''
        chapter_text = self.controller.matchStats.get_chapters(self.controller.startTime)
        self.textChapters.configure(state="normal")
        self.textChapters.delete("1.0", tk.END)
        self.textChapters.insert(tk.END, chapter_text)
        self.textChapters.configure(state="disabled")
    
    def _go_back(self, e=None):
        self.controller.frames["MatchEntryPage"].clear_entries()
        self.controller.show_frame("MatchEntryPage")




win = ChapterPrinter()
style = ttk.Style(win)
style.configure("Placeholder.TEntry", foreground="#d5d5d5")

win.geometry("400x240+100+100")
win.mainloop()

