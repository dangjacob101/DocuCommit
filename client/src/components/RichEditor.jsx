import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Placeholder from '@tiptap/extension-placeholder'
import { TextStyle, FontSize } from '@tiptap/extension-text-style'
import { useEffect, useState } from 'react'

const FONT_SIZES = ['12px', '14px', '16px', '18px', '20px', '24px', '28px', '32px']

export default function RichEditor({ content, onUpdate, placeholder }) {
  const [, forceUpdate] = useState(0)
  const editor = useEditor({
    onTransaction: () => forceUpdate(n => n + 1),
    onSelectionUpdate: () => forceUpdate(n => n + 1),
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      Underline,
      Placeholder.configure({
        placeholder: placeholder || 'Start typing...',
      }),
      TextStyle,
      FontSize,
    ],
    content: content || '',
    onUpdate: ({ editor }) => {
      onUpdate(JSON.stringify(editor.getJSON()))
    },
  })

  useEffect(() => {
    if (!editor) return
    let incoming
    try {
      incoming = content ? JSON.parse(content) : ''
    } catch {
      incoming = content || ''
    }
    const current = JSON.stringify(editor.getJSON())
    if (content !== current) {
      editor.commands.setContent(incoming, false)
    }
  }, [content])

  if (!editor) return null

  return (
    <div className="rich-editor-wrapper">
      <div className="toolbar">
        <button
          type="button"
          className={`toolbar-btn${editor.isActive('bold') ? ' active' : ''}`}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => editor.chain().focus().toggleBold().run()}
          title="Bold (Ctrl+B)"
        >
          <strong>B</strong>
        </button>

        <button
          type="button"
          className={`toolbar-btn${editor.isActive('italic') ? ' active' : ''}`}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => editor.chain().focus().toggleItalic().run()}
          title="Italic (Ctrl+I)"
        >
          <em>I</em>
        </button>

        <button
          type="button"
          className={`toolbar-btn${editor.isActive('underline') ? ' active' : ''}`}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          title="Underline (Ctrl+U)"
        >
          <u>U</u>
        </button>

        <span className="toolbar-divider" />

        <select
          className="toolbar-select"
          value={editor.getAttributes('textStyle').fontSize || ''}
          onChange={(e) => {
            const size = e.target.value
            if (size) {
              editor.chain().focus().setFontSize(size).run()
            } else {
              editor.chain().focus().unsetFontSize().run()
            }
          }}
          title="Font size"
        >
          <option value="">Size</option>
          {FONT_SIZES.map(s => (
            <option key={s} value={s}>{parseInt(s)}pt</option>
          ))}
        </select>
      </div>

      <EditorContent editor={editor} className="rich-editor-content" />
    </div>
  )
}
