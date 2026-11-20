;;; nitpick-mode.el --- Major mode for Nitpick (.npk) -*- lexical-binding: t -*-

;; First written by Muse Wonder (Meta); checked by Nitpick management
;; (Claude Opus 5.5).
;;
;; Built from the lexer tables at nitpick commit aefae6e (src/frontend/
;; keywords.npk, lexer.npk, numeric.npk, num_width.npk, escapes.npk,
;; operators.npk); keyword grouping as in the checked TextMate grammar,
;; nanorc and vim syntax file.

;;; Commentary:

;; A small major mode for Nitpick source files.  Strings, characters and
;; comments are recognised by Emacs's syntax parser via the syntax table
;; (so a // or /* inside a string stays a string); font-lock adds the
;; keyword, type, number, escape and operator faces on top.
;;
;; `syntax-propertize-function' handles the two string forms the syntax
;; table cannot express on its own: """ block strings (via generic
;; string fences on the outer quote characters) and r"..." raw strings
;; (backslashes inside lose their escape syntax, matching the lexer,
;; which does no escape processing there).  Backtick templates are
;; string-delimited by the syntax table and fontified as strings whole;
;; &{ ... } interpolation is not fontified separately.

;;; Code:

;; The Emacs 29 faces used below for operators, brackets, delimiters
;; and escapes exist as faces but, unlike the classic font-lock faces,
;; have no variable bound to them in a bare session; font-lock
;; evaluates the face name in a keyword spec as a variable, so bind
;; them (defvar is a no-op where a value already exists).
(defvar font-lock-operator-face 'font-lock-operator-face)
(defvar font-lock-bracket-face 'font-lock-bracket-face)
(defvar font-lock-delimiter-face 'font-lock-delimiter-face)
(defvar font-lock-escape-face 'font-lock-escape-face)

;;;; Keyword groups (every word of keywords.npk: 170, grouped as in the
;;;; checked TextMate grammar / nanorc / vim file).

(defconst nitpick--control-keywords
  '("if" "else" "for" "while" "loop" "break" "continue" "return"
    "pass" "exit" "fail" "defer" "pick" "when" "fall" "then"
    "till" "end" "in" "is" "as" "on" "with" "where")
  "Nitpick control-flow keywords (24).")

(defconst nitpick--contract-keywords
  '("requires" "ensures" "decreases" "invariant" "old" "result"
    "limit" "prove" "assert_static")
  "Nitpick contract keywords (9).")

(defconst nitpick--safety-keywords
  '("wild" "wildx" "raw" "move" "drop" "discard" "relay" "give"
    "gives" "acquires" "joins" "never" "fails")
  "Nitpick safety/ownership keywords (13).")

(defconst nitpick--async-keywords
  '("async" "await" "thread")
  "Nitpick async keywords (3).")

(defconst nitpick--memorder-keywords
  '("acquire" "release" "acq_rel" "seq_cst" "relaxed")
  "Nitpick memory-order keywords (5).")

(defconst nitpick--builtin-fn-keywords
  '("is_err" "range")
  "Nitpick built-in function keywords (2).")

(defconst nitpick--decl-keywords
  '("func" "struct" "enum" "trait" "impl" "mod" "use" "error"
    "unit" "macro" "extern")
  "Nitpick declaration keywords (11).")

(defconst nitpick--modifier-keywords
  '("pub" "fixed" "sealed" "hidden" "pure" "inline" "noinline" "nodrop"
    "opaque" "assoc" "defaults" "comptime" "cfg" "derive" "unbounded")
  "Nitpick modifier keywords (15).")

(defconst nitpick--constant-keywords
  '("true" "false" "NIL" "NULL" "ERR")
  "Nitpick language constants (5).  NIL, NULL and ERR are constants,
not types -- listing them here, before the capitalised-name rule, and
font-lock's no-override default keep them from being repainted as
types (the nano file's bug).")

(defconst nitpick--type-keywords
  '("any" "dyn" "bool" "char8" "char16" "char32"
    "int8" "int16" "int32" "int64" "int128" "int256" "int512" "int1024"
    "int2048" "int4096"
    "uint8" "uint16" "uint32" "uint64" "uint128" "uint256" "uint512"
    "uint1024" "uint2048" "uint4096"
    "flt32" "flt64" "flt128" "flt256" "flt512"
    "frac8" "frac16" "frac32" "frac64"
    "tfp32" "tfp64" "tfp128" "tfp256"
    "tbb8" "tbb16" "tbb32" "tbb64" "tbb128" "tbb256"
    "dim256" "nit" "trit" "tryte" "nyte"
    "string" "cstring" "buffer" "atomic" "array" "simd" "complex"
    "arena" "shared_arena" "stack"
    "Result" "Optional" "Future" "Handle" "Guard" "Mutex" "RGuard"
    "RwLock" "Barrier" "Channel" "CondVar" "OwnedFd" "Self" "Rules"
    "pid" "tid" "uid" "gid" "fd" "prot" "oflags" "mflags" "fmode")
  "Nitpick built-in type keywords (83).")

;;;; Numbers (numeric.npk / num_width.npk).
;;
;; Bases are spelled as suffixes -- hex, bin, oct, ter/tri/t, non/n --
;; never 0x/0b prefixes.  A float must contain a dot (FloatLiteral ::=
;; DecimalLiteral "." DecimalLiteral Exponent? TypeSuffix?), so 1e3 is
;; not a float.  flt128 is storage-only (D-143) and has no literals:
;; there is deliberately no f128 suffix anywhere below.

(defconst nitpick--number-regexp
  (let* ((width "\\(?:8\\|16\\|32\\|64\\|128\\|256\\|512\\|1024\\|2048\\|4096\\)")
         (intsuf (concat "\\(?:\\(?:i\\|u\\)" width
                         "\\|tbb\\(?:8\\|16\\|32\\|64\\|128\\|256\\)\\)"))
         (floatsuf "\\(?:f32\\|f64\\|tfp32\\|tfp64\\|tfp128\\|tfp256\\|dim256\\)"))
    (mapconcat
     #'identity
     (list
      (concat "\\_<[0-9][0-9_]*" intsuf "\\_>")
      (concat "\\_<[0-9][0-9_]*\\(?:char8\\|char16\\|char32\\)\\_>")
      (concat "\\_<[0-9][0-9A-Fa-f_]*hex" intsuf "?\\_>")
      (concat "\\_<[01][01_]*bin" intsuf "?\\_>")
      (concat "\\_<[0-7][0-7_]*oct" intsuf "?\\_>")
      (concat "\\_<[01][01Tt_]*\\(?:ter\\|tri\\|t\\)" intsuf "?\\_>")
      (concat "\\_<[0-4][0-4A-Da-d_]*\\(?:non\\|n\\)" intsuf "?\\_>")
      (concat "\\_<[0-9][0-9_]*" floatsuf "\\_>")
      (concat "\\_<[0-9][0-9_]*\\.[0-9][0-9_]*"
              "\\(?:[eE][-+]?[0-9][0-9_]*\\)?" floatsuf "?\\_>")
      "\\_<[0-9][0-9_]*\\_>")
     "\\|"))
  "Regexp matching every Nitpick number literal form.")

;;;; Type:name declarations.
;;
;; A single forward match: a type word, a colon, then the declared
;; name.  There is no backward search and no lookbehind anywhere in
;; this mode (the vim file's Type:name lookbehind over a long
;; alternation cost ~4 ms per line there; this regexp is one
;; `regexp-opt' trie plus a capitalised-name alternative, matched
;; forward like every other font-lock rule).  Only Type:name is done
;; -- mod:name and func:name are not.

(defconst nitpick--decl-name-regexp
  (concat "\\<\\(" (regexp-opt nitpick--type-keywords)
          "\\|[A-Z][A-Za-z0-9_]*\\)\\s-*:\\s-*\\(\\_<[A-Za-z0-9_]*\\_>\\)")
  "Regexp matching a Type:name declaration.
Group 1 is the type, group 2 the declared name.")

;;;; Operators (operators.npk).  Multi-character spellings come first
;;;; in the alternation so they win over their single-character
;;;; prefixes at the same position.

(defconst nitpick--operator-regexp
  ;; Every literal ? is written [?] on purpose: a bare ?? branch is
  ;; "optional ?", which matches the empty string, and an alternation
  ;; branch that can match empty shadows every later branch in
  ;; font-lock (the first face dump painted only the ? operators and
  ;; left the rest plain).  [?] cannot match empty.
  (concat "=>!\\|[?][?]!\\|[?]!\\|[?]|\\|[?]\\.\\|[?][?]"
          "\\|\\.\\.\\*\\|\\.\\.\\.\\|\\.\\.\\^\\|\\.\\."
          "\\|<=>\\|=>\\|<-\\|->\\|<<=\\|>>=\\|<<\\|>>\\|<=\\|>=\\|==\\|!="
          "\\|+%\\|+%=\\|\\*%\\|\\*%=\\|-%\\|-%=\\|&&\\|||\\|\\+\\+\\|--"
          "\\|+=\\|-=\\|\\*=\\|%=\\|/=\\|&=\\|\\^=\\||=\\|!!!\\|<|\\||>"
          "\\|\\$\\$[im]\\|_[?!~^]\\|::<\\|[$@+*/%=<>!&|^~#?-]")
  "Regexp matching Nitpick operators (brackets and : ; , . excluded;
those have their own rules).")

;;;; Escapes (escapes.npk: \\ \n \r \t \" \' \0, \xHH and \u{...}).
;;
;; A function matcher, so escapes are coloured only where the syntax
;; parser says we are inside a string or character -- and not inside
;; raw strings (no escape processing there) or templates.

(defconst nitpick--escape-regexp
  "\\\\\\(?:u{[0-9a-fA-F]+}\\|x[0-9a-fA-F]\\{2\\}\\|.\\)"
  "Regexp matching one Nitpick escape sequence.")

(defun nitpick--escape-matcher (limit)
  "Font-lock matcher for escape sequences, up to LIMIT.
Matches only inside plain/block strings and characters, as reported
by `syntax-ppss'; raw strings and templates are skipped."
  (let (found)
    (while (and (not found)
                (re-search-forward nitpick--escape-regexp limit t))
      ;; save-excursion: syntax-ppss leaves point at the position
      ;; parsed to, which would disturb font-lock's search loop.
      (let ((state (save-excursion
                     (syntax-ppss (match-beginning 0)))))
        (when (and (nth 3 state)                ; inside a string/char
                   (not (eq (nth 3 state) ?`))  ; not a template
                   (not (and (nth 8 state)      ; not a raw string
                             (> (nth 8 state) (point-min))
                             (eq (char-before (nth 8 state)) ?r))))
          (setq found t))))
    found))

;;;; Font-lock.

(defvar nitpick-font-lock-keywords
  (list
   ;; Type:name first, so the declared name keeps its own face.
   (list nitpick--decl-name-regexp
         '(1 font-lock-type-face)
         '(2 font-lock-variable-name-face))
   (cons (regexp-opt nitpick--control-keywords 'words)
         'font-lock-keyword-face)
   (cons (regexp-opt nitpick--contract-keywords 'words)
         'font-lock-preprocessor-face)
   (cons (regexp-opt nitpick--safety-keywords 'words)
         'font-lock-keyword-face)
   (cons (regexp-opt nitpick--async-keywords 'words)
         'font-lock-keyword-face)
   (cons (regexp-opt nitpick--memorder-keywords 'words)
         'font-lock-constant-face)
   (cons (regexp-opt nitpick--builtin-fn-keywords 'words)
         'font-lock-builtin-face)
   (cons (regexp-opt nitpick--decl-keywords 'words)
         'font-lock-keyword-face)
   (cons (regexp-opt nitpick--modifier-keywords 'words)
         'font-lock-keyword-face)
   (cons (regexp-opt nitpick--constant-keywords 'words)
         'font-lock-constant-face)
   (cons (regexp-opt nitpick--type-keywords 'words)
         'font-lock-type-face)
   ;; Capitalised names that are not keywords: user and prelude types
   ;; (Meters, Seconds, MyStruct, ...).
   (cons "\\<[A-Z][A-Za-z0-9_]*\\>" 'font-lock-type-face)
   (cons nitpick--number-regexp 'font-lock-constant-face)
   ;; OVERRIDE t: the syntactic pass has already painted the string;
   ;; without it font-lock would leave the string face in place.
   ;; The matcher only fires inside strings/chars, so this is safe.
   (list 'nitpick--escape-matcher '(0 font-lock-escape-face t))
   (cons nitpick--operator-regexp 'font-lock-operator-face)
   (cons "[][(){}]" 'font-lock-bracket-face)
   (cons "[:,.;]" 'font-lock-delimiter-face))
  "Font-lock keywords for `nitpick-mode'.")

;;;; Syntax table.
;;
;; // and /* */ comments (style b for the line comment, as in C).
;; Block comments end at the first */ -- Nitpick block comments do not
;; nest, and neither does this table.  " delimits strings, ' delimits
;; characters (fontified as strings), ` delimits templates, and \ is
;; the escape character -- so the syntax parser, not regexps, decides
;; what is a string or a comment.

(defvar nitpick-mode-syntax-table
  (let ((table (make-syntax-table)))
    (modify-syntax-entry ?/ ". 124b" table)
    (modify-syntax-entry ?* ". 23" table)
    (modify-syntax-entry ?\n "> b" table)
    (modify-syntax-entry ?' "\"" table)
    (modify-syntax-entry ?` "\"" table)
    ;; _ is a word constituent in Nitpick identifiers (is_err,
    ;; returns_x, assert_static are single words).  With the standard
    ;; table's symbol syntax for _, \<is\> would match inside is_err
    ;; and paint its `is' as the keyword (seen in the first dump).
    (modify-syntax-entry ?_ "w" table)
    table)
  "Syntax table for `nitpick-mode'.")

;;;; syntax-propertize: block strings and raw strings.
;;
;; The state checks below use `parse-partial-sexp' directly, never
;; `syntax-ppss', and wrap it in `save-excursion'.  Both parsers
;; leave point at the position parsed to; inside a
;; `syntax-propertize-rules' loop, which continues its search from
;; point, that makes the loop find the same fence again forever
;; (found the hard way -- a buffer with one block string never
;; finished propertizing).  parse-partial-sexp also reads the syntax
;; table and whatever syntax-table properties are already in place,
;; including fences applied earlier in the same pass.  Calls within
;; a pass arrive in increasing position order, so the parse state is
;; threaded through a cache that each pass resets.

(defvar-local nitpick--parse-cache nil
  "Cache for `nitpick--state-at': (POSITION . STATE) of the last parse.")

(defun nitpick--state-at (pos)
  "Return the parse state at POS, computed with `parse-partial-sexp'.
Threads the state through `nitpick--parse-cache' so a pass over a
buffer costs one left-to-right parse, not one parse per fence."
  (unless (and nitpick--parse-cache
               (<= (car nitpick--parse-cache) pos))
    (setq nitpick--parse-cache (cons (point-min) nil)))
  (let ((state (save-excursion
                 (parse-partial-sexp (car nitpick--parse-cache) pos
                                      nil nil (cdr nitpick--parse-cache)))))
    (setq nitpick--parse-cache (cons pos state))
    state))

(defun nitpick--propertize-triple-quote (pos)
  "Handle a \"\"\" occurrence at POS for `syntax-propertize-function'.
An opening fence gets a generic string fence (syntax `|') on its
first quote, and the closing fence -- found by a forward search, as
the lexer ends a block string at the first \"\"\" -- on its last
quote.  A closing fence seen again later in the same pass is
recognised by the fence property at the string's start and simply
re-marked.  Occurrences inside ordinary strings or comments are
left alone."
  (let ((state (nitpick--state-at pos)))
    (cond
     ((nth 4 state) nil)                    ; inside a comment
     ((nth 3 state)                         ; inside a string
      (when (eq (get-text-property (nth 8 state) 'syntax-table)
                (string-to-syntax "|"))
        (put-text-property (+ pos 2) (+ pos 3)
                           'syntax-table (string-to-syntax "|"))))
     (t                                     ; opening fence
      (put-text-property pos (1+ pos)
                         'syntax-table (string-to-syntax "|"))
      (save-excursion
        (goto-char (+ pos 3))
        (when (search-forward "\"\"\"" nil t)
          (put-text-property (- (point) 1) (point)
                             'syntax-table (string-to-syntax "|"))))))))

(defun nitpick--propertize-raw-string (pos)
  "Handle an r\" at POS for `syntax-propertize-function'.
Nitpick raw strings do no escape processing (lexer D-024) and end
at the first \" on the line, so every backslash up to that quote
loses its escape syntax; the string then parses as an ordinary
string whose backslashes are literal content."
  (let ((state (nitpick--state-at pos)))
    (unless (or (nth 3 state) (nth 4 state))
      (save-excursion
        (goto-char (+ pos 2))
        (when (search-forward "\"" (line-end-position) t)
          (let ((close (1- (point)))
                (p (+ pos 2)))
            (while (< p close)
              (when (eq (char-after p) ?\\)
                (put-text-property p (1+ p)
                                   'syntax-table (string-to-syntax ".")))
              (setq p (1+ p)))))))))

(defconst nitpick--propertize-rules
  (syntax-propertize-rules
   ("\"\"\"" (0 (ignore (nitpick--propertize-triple-quote
                         (match-beginning 0)))))
   ("\\_<r\"" (0 (ignore (nitpick--propertize-raw-string
                          (match-beginning 0))))))
  "The propertize rules for `nitpick-mode'.")

(defun nitpick-syntax-propertize (start end)
  "Value for `syntax-propertize-function' in `nitpick-mode'.
Resets the parse cache, then applies `nitpick--propertize-rules'
between START and END."
  (setq nitpick--parse-cache nil)
  (funcall nitpick--propertize-rules start end))

;;;; The mode itself.

;;;###autoload
(define-derived-mode nitpick-mode prog-mode "Nitpick"
  "Major mode for Nitpick (.npk) source files."
  :syntax-table nitpick-mode-syntax-table
  (setq-local font-lock-defaults '(nitpick-font-lock-keywords))
  (setq-local syntax-propertize-function #'nitpick-syntax-propertize)
  (setq-local comment-start "// ")
  (setq-local comment-end "")
  (setq-local comment-start-skip "\\(?://\\|/\\*+\\)\\s-*"))

;;;###autoload
(add-to-list 'auto-mode-alist '("\\.npk\\'" . nitpick-mode))

(provide 'nitpick-mode)
;;; nitpick-mode.el ends here
