import ValFunc as vf
# import ImgageOpenURL
import re
import customtkinter as ctk


class ChapterPrinter(ctk.CTk):
    """Window of program"""
    def __init__(self, *args, **kwargs):
        ctk.CTk.__init__(self, *args, **kwargs)
        self.title("Chapter Printer")
        self.geometry("400x240+100+100")
        
        self.puuid: str | None = None
        self.chapterStr: vf.MatchStats | None = None
        self.startTime: int | None = None


        container = ctk.CTkFrame(self)
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
    
    def copy_to_clip(self, field):
        '''Copy the given field value to the clipboard'''
        self.clipboard_clear()
        self.clipboard_append(field.get("1.0", ctk.END).rstrip())


class GTEntryPage(ctk.CTkFrame):
    """First page of program, for entering Riot ID"""
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self, parent)
        self.controller = controller
        
        self.riotID: str | None = None
        
        rIDlabel = ctk.CTkLabel(self, text="Riot ID:")
        rIDlabel.grid(row=1, column=1, pady=10, padx=5)
        
        self.rIDentry = ctk.CTkEntry(self, placeholder_text="username#TAG")
        self.rIDentry.grid(row=1, column=2, pady=10)
        self.rIDentry.bind("<Return>", self._check_RiotID)
        
        buttonEnter = ctk.CTkButton(self, text="Enter", command=self._check_RiotID)
        buttonEnter.grid(row=2, column=1, columnspan=2)
        
        self.warningStr = ctk.StringVar()
        warningLable = ctk.CTkLabel(self, textvariable=self.warningStr, width=35, height=0, wraplength=200)
        warningLable.grid(row=3, column=1, columnspan=2, pady=10)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(3, weight=1)
    
    def _check_RiotID(self, e=None):
        if not self.rIDentry.get(): # if empty
            self.warningStr.set("Please enter Riot ID")
            return
        elif self.riotID != self.rIDentry.get().rstrip():
            try:
                username, tagline = vf.str_to_user_gt(self.rIDentry.get())
                self.controller.puuid = vf.gt_to_puuid(username, tagline)
                self.riotID = self.rIDentry.get().rstrip()
            except Exception as e:
                self.warningStr.set(e)
                return
        self.controller.show_frame("MatchEntryPage")
    
            


class MatchEntryPage(ctk.CTkFrame):
    """Match and time entry page"""
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self, parent)
        self.controller = controller
        
        mIDlabel = ctk.CTkLabel(self, text="Match ID:")
        mIDlabel.grid(row=1, column=1, pady=10)
        
        self.mIDentry = ctk.CTkEntry(self, placeholder_text="00000000-0000-0000-0000-000000000000")
        self.mIDentry.grid(row=1, column=2, pady=10)
        self.mIDentry.bind("<Return>", self._lookup_match)
        
        timeLabel = ctk.CTkLabel(self, text="End of 1st pre-round:")
        timeLabel.grid(row=2, column=1, pady=10)
        
        self.timeEntry = ctk.CTkEntry(self, placeholder_text="h:mm:ss / mm:ss / sss")
        self.timeEntry.grid(row=2, column=2, pady=(0, 10))
        self.timeEntry.bind("<Return>", self._lookup_match)
        
        buttonBack = ctk.CTkButton(self, text="Go back", command=lambda: self.controller.show_frame("GTEntryPage"))
        buttonBack.grid(row=3, column=1, padx=(0, 5))
        
        buttonEnter = ctk.CTkButton(self, text="Enter", command=self._lookup_match)
        buttonEnter.grid(row=3, column=2)
        
        self.warningStr = ctk.StringVar()
        warningLable = ctk.CTkLabel(self, textvariable=self.warningStr, width=37, height=0, wraplength=220)
        warningLable.grid(row=4, column=1, columnspan=2, pady=10)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(3, weight=1)
    
    def _lookup_match(self, e=None):
        if not self.mIDentry.get(): # if empty
            self.warningStr.set("Please enter Match ID")
            return
        matchID = self.mIDentry.get().rstrip()
        if not self._verify_match_id_format(matchID):
            self.warningStr.set("Invalid match ID format")
            return
        
        if not self.timeEntry.get(): # if empty
            self.warningStr.set("Please enter time")
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
            tempMatchStats = vf.MatchStats(matchID, self.controller.puuid)
        except Exception as e:
            self.warningStr.set(e)
            return
        self.controller.matchStats = tempMatchStats
        self.controller.frames["ChaptersPage"].update_text()
        self.controller.show_frame("ChaptersPage")
    
    def _verify_match_id_format(self, match_id):
        pattern = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        return pattern.match(match_id) is not None
    
    def clear_entries(self):
        '''Clears the entries in the match ID entry field and the time entry field'''
        self.mIDentry.delete(0, ctk.END)
        self.timeEntry.delete(0, ctk.END)

class ChaptersPage(ctk.CTkFrame):
    """Chapters page to copy chapters to clipboard"""
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self, parent)
        self.controller = controller
        
        buttonCopy = ctk.CTkButton(self, text="Copy to clipboard", command=lambda: controller.copy_to_clip(self.textChapters))
        buttonCopy.grid(row=1, column=1, pady=10)
        
        buttonBack = ctk.CTkButton(self, text="New match", command=self._go_back)
        buttonBack.grid(row=1, column=2, pady=10)
        
        self.textChapters = ctk.CTkTextbox(self, width=300, height=180, state="disabled")
        self.textChapters.grid(row=2, column=1, columnspan=2)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(3, weight=1)

    def update_text(self):
        '''Updates the text in the textChapters widget with the chapters obtained from the matchStats object'''
        chapter_text = self.controller.matchStats.get_chapters(self.controller.startTime)
        self.textChapters.configure(state="normal")
        self.textChapters.delete("1.0", ctk.END)
        self.textChapters.insert(ctk.END, chapter_text)
        self.textChapters.configure(state="disabled")
    
    def _go_back(self, e=None):
        self.controller.frames["MatchEntryPage"].clear_entries()
        self.controller.show_frame("MatchEntryPage")



if __name__ == "__main__":
    win = ChapterPrinter()
    win.mainloop()

