package sample

func ParseConfig(path string) string {
	return path
}

type Server struct{}

func (s *Server) HandleRequest(name string) string {
	return name
}

func helperLower() {}
