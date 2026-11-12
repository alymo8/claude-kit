class Formatter
  def self.build(options)
    new(options)
  end

  def render(text)
    text
  end

  def valid?
    true
  end
end
